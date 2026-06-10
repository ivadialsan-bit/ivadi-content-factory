from fastapi import APIRouter
import json
import os
import subprocess

router = APIRouter(prefix="/api/ivadi", tags=["ivadi"])

QUEUE_FILE = "/root/factory/ivadi_queue.json"
LOG_FILE = "/root/factory/ivadi_posts_log.json"


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []


def save_queue(queue):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


@router.get("/queue")
def get_queue():
    queue = load_queue()
    return {
        "total": len(queue),
        "pending": len([p for p in queue if p["status"] == "pending"]),
        "published": len([p for p in queue if p["status"] == "published"]),
        "rejected": len([p for p in queue if p["status"] == "rejected"]),
        "posts": queue[-50:]
    }


@router.post("/queue/{post_id}/publish")
def publish_post(post_id: int):
    import sys
    sys.path.insert(0, "/root/factory")
    from ivadi_queue import mark_published
    from ivadi_scheduler import send_to_max_channel

    queue = load_queue()
    post = next((p for p in queue if p["id"] == post_id), None)
    if not post:
        return {"error": "Пост не найден"}

    ok = send_to_max_channel(post["text"])
    if ok:
        mark_published(post_id)
        return {"success": True, "message": "Опубликован"}
    return {"success": False, "message": "Ошибка отправки в MAX"}


@router.post("/queue/{post_id}/reject")
def reject_post(post_id: int):
    queue = load_queue()
    for p in queue:
        if p["id"] == post_id:
            p["status"] = "rejected"
            break
    save_queue(queue)
    return {"success": True}


@router.post("/generate")
def generate_queue():
    result = subprocess.run(
        ["python3", "/root/factory/ivadi_generate_queue.py"],
        capture_output=True, text=True, cwd="/root/factory"
    )
    return {
        "success": result.returncode == 0,
        "output": result.stdout[-500:] if result.stdout else "",
        "error": result.stderr[-300:] if result.stderr else ""
    }


@router.get("/stats")
def get_stats():
    log = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                log = json.load(f)
            except:
                log = []

    total = len(log)
    success = len([l for l in log if l.get("success")])
    today = [l for l in log if l.get("datetime", "").startswith(
        __import__("datetime").datetime.now().strftime("%Y-%m-%d")
    )]

    by_type = {}
    for l in log:
        t = l.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1

    return {
        "total_published": total,
        "success_rate": round(success / total * 100) if total else 0,
        "today_count": len(today),
        "by_type": by_type,
        "recent": log[-10:]
    }


@router.get("/service")
def get_service_status():
    result = subprocess.run(
        ["systemctl", "is-active", "ivadi-content"],
        capture_output=True, text=True
    )
    return {
        "status": result.stdout.strip(),
        "running": result.stdout.strip() == "active"
    }
