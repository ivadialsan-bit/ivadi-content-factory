import requests
import time
import jwt
import json
from datetime import datetime
from config import KLING_ACCESS_KEY, KLING_SECRET_KEY

def generate_jwt():
    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5
    }
    return jwt.encode(payload, KLING_SECRET_KEY, algorithm="HS256")

def create_video(prompt, duration=5):
    token = generate_jwt()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "kling-v1",
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "9:16"
    }
    response = requests.post(
        "https://api.klingai.com/v1/videos/text2video",
        headers=headers,
        json=data
    )
    return response.json()

def check_status(task_id):
    token = generate_jwt()
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"https://api.klingai.com/v1/videos/text2video/{task_id}",
        headers=headers
    )
    return response.json()

def wait_for_video(task_id, max_wait=300):
    print(f"Ждём видео {task_id}...")
    for i in range(max_wait // 10):
        result = check_status(task_id)
        status = result.get("data", {}).get("task_status", "")
        print(f"Статус: {status}")
        if status == "succeed":
            videos = result["data"]["task_result"]["videos"]
            return videos[0]["url"]
        elif status == "failed":
            print("Ошибка генерации")
            return None
        time.sleep(10)
    return None

if __name__ == "__main__":
    prompt = "A black hole pulling a star apart, cinematic, space, 4k, dramatic lighting"
    print(f"Генерируем: {prompt}")
    result = create_video(prompt)
    print(json.dumps(result, indent=2))
    task_id = result.get("data", {}).get("task_id")
    if task_id:
        url = wait_for_video(task_id)
        if url:
            print(f"Видео готово: {url}")
