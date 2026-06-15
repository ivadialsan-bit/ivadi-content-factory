from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from models import Opportunity, TgChannel
from datetime import datetime

router = APIRouter(prefix="/api/opportunities")

@router.get("")
def get_opportunities(db: Session = Depends(get_db)):
    items = db.query(Opportunity).order_by(Opportunity.score.desc(), Opportunity.created_at.desc()).limit(100).all()
    return [{"id": o.id, "channel": o.channel, "text": o.text[:300], "score": o.score,
             "score_reason": o.score_reason, "category": o.category, "status": o.status,
             "posted_at": str(o.posted_at), "created_at": str(o.created_at)} for o in items]

@router.patch("/{opp_id}/status")
def update_status(opp_id: int, data: dict, db: Session = Depends(get_db)):
    o = db.query(Opportunity).filter(Opportunity.id == opp_id).first()
    if o:
        o.status = data.get("status", o.status)
        db.commit()
    return {"ok": True}

@router.get("/channels")
def get_channels(db: Session = Depends(get_db)):
    items = db.query(TgChannel).order_by(TgChannel.created_at.desc()).all()
    return [{"id": c.id, "username": c.username, "title": c.title,
             "is_active": c.is_active, "last_checked_at": str(c.last_checked_at)} for c in items]

@router.post("/channels")
def add_channel(data: dict, db: Session = Depends(get_db)):
    username = data.get("username", "").strip().lstrip("@")
    existing = db.query(TgChannel).filter(TgChannel.username == username).first()
    if existing:
        return {"ok": False, "error": "already exists"}
    ch = TgChannel(username=username, title=data.get("title", username), is_active=True)
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return {"ok": True, "id": ch.id}

@router.delete("/channels/{ch_id}")
def delete_channel(ch_id: int, db: Session = Depends(get_db)):
    ch = db.query(TgChannel).filter(TgChannel.id == ch_id).first()
    if ch:
        db.delete(ch)
        db.commit()
    return {"ok": True}


@router.post("/ingest")
def ingest_opportunities(data: dict, db: Session = Depends(get_db)):
    items = data.get("items", [])
    saved = 0
    for item in items:
        existing = db.query(Opportunity).filter(
            Opportunity.tg_message_id == item["tg_message_id"],
            Opportunity.channel == item["channel"]
        ).first()
        if existing:
            continue
        o = Opportunity(
            tg_message_id=item["tg_message_id"],
            channel=item["channel"],
            text=item["text"],
            score=item.get("score", 0),
            score_reason=item.get("score_reason", ""),
            category=item.get("category", ""),
            posted_at=datetime.fromisoformat(item["posted_at"]) if item.get("posted_at") else None
        )
        db.add(o)
        saved += 1
    db.commit()
    return {"ok": True, "saved": saved}


@router.post("/ingest")
def ingest_opportunities(data: dict, db: Session = Depends(get_db)):
    items = data.get("items", [])
    saved = 0
    for item in items:
        existing = db.query(Opportunity).filter(
            Opportunity.tg_message_id == item["tg_message_id"],
            Opportunity.channel == item["channel"]
        ).first()
        if existing:
            continue
        o = Opportunity(
            tg_message_id=item["tg_message_id"],
            channel=item["channel"],
            text=item["text"],
            score=item.get("score", 0),
            score_reason=item.get("score_reason", ""),
            category=item.get("category", ""),
            posted_at=datetime.fromisoformat(item["posted_at"]) if item.get("posted_at") else None
        )
        db.add(o)
        saved += 1
    db.commit()
    return {"ok": True, "saved": saved}

@router.post("/run")
def run_hunter():
    import subprocess
    subprocess.Popen(["python3", "/root/factory/opportunity_hunter.py"])
    return {"ok": True, "message": "Hunter started"}
