import requests
import io
import os
import time
import json
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv

load_dotenv('/root/factory/.ivadi.env')

LEONARDO_API_KEY = os.getenv("LEONARDO_API_KEY", "d42c2467-3d55-43b4-8ce7-fa760ffba0c6")
LEONARDO_MODEL_ID = "b24e16ff-06e3-43eb-8d33-4416c2d75876"  # Leonardo Phoenix
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")
CLOUDFLARE_PROXY = os.getenv("CLAUDE_PROXY_URL", "https://anthropic-proxy.ivadialsan.workers.dev/v1/messages")

OUTPUT_DIR = "/root/factory/output/ivadi"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Стили по платформе
PLATFORM_STYLES = {
    "max":       "cinematic travel photography, golden hour, ultra realistic, 4k, no text",
    "vk":        "cinematic travel photography, dramatic lighting, vivid colors, 4k, no text",
    "instagram": "vibrant travel lifestyle, warm tones, instagram aesthetic, beautiful destination, no text",
    "telegram":  "cinematic travel photography, wide angle, epic landscape, 4k, no text",
    "default":   "cinematic travel photography, golden hour lighting, ultra realistic, 4k, no text"
}

def generate_prompt_from_text(post_text: str, platform: str = "default") -> str:
    """Генерирует визуальный промпт через Claude на основе текста поста"""
    style = PLATFORM_STYLES.get(platform, PLATFORM_STYLES["default"])
    
    system = (
        "Ты генерируешь короткие визуальные промпты для AI-генерации изображений. "
        "Отвечай ТОЛЬКО промптом на английском языке, без объяснений, без кавычек. "
        "Промпт должен описывать конкретную визуальную сцену которая максимально соответствует тексту поста. "
        "Длина: 1-2 предложения."
    )
    
    user = (
        f"Текст поста:\n{post_text[:500]}\n\n"
        f"Платформа: {platform}\n"
        f"Обязательный стиль: {style}\n\n"
        "Напиши визуальный промпт для изображения к этому посту."
    )
    
    try:
        # Пробуем через Cloudflare прокси
        r = requests.post(
            CLOUDFLARE_PROXY,
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 200,
                "system": system,
                "messages": [{"role": "user", "content": user}]
            },
            timeout=30
        )
        if r.status_code == 200:
            prompt = r.json()["content"][0]["text"].strip()
            print(f"   [Claude] Промпт: {prompt[:80]}...")
            return prompt
    except Exception as e:
        print(f"   [Claude] Ошибка: {e}, используем fallback")
    
    # Fallback — берём первые 100 символов текста + стиль
    short = post_text[:100].replace('\n', ' ')
    return f"{short}. {style}"


def generate_image(post_text: str, platform: str = "default", output_path: str = None) -> dict:
    """
    Главная функция. Принимает текст поста и платформу.
    Возвращает dict: {success, image_path, prompt, url}
    """
    print(f"   [Leonardo Auto] Платформа: {platform}")
    
    # 1. Генерируем промпт
    prompt = generate_prompt_from_text(post_text, platform)
    
    # 2. Путь для сохранения
    if not output_path:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"{OUTPUT_DIR}/auto_{platform}_{ts}.jpg"
    
    # 3. Генерируем через Leonardo
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "modelId": LEONARDO_MODEL_ID,
        "width": 1280,
        "height": 720,
        "num_images": 1,
        "guidance_scale": 7,
        "alchemy": True
    }
    
    try:
        r = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/generations",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if r.status_code != 200:
            print(f"   [Leonardo] Ошибка запуска: {r.status_code} {r.text[:100]}")
            return {"success": False, "error": r.text}
        
        gen_id = r.json()["sdGenerationJob"]["generationId"]
        print(f"   [Leonardo] ID: {gen_id}, ждём...")
        
        # Поллинг
        for attempt in range(24):
            time.sleep(5)
            r2 = requests.get(
                f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}",
                headers=headers,
                timeout=30
            )
            if r2.status_code != 200:
                continue
            
            data = r2.json().get("generations_by_pk", {})
            status = data.get("status")
            
            if status == "COMPLETE":
                images = data.get("generated_images", [])
                if images:
                    img_url = images[0]["url"]
                    img_resp = requests.get(img_url, timeout=30)
                    img = Image.open(io.BytesIO(img_resp.content))
                    img.save(output_path, "JPEG", quality=95)
                    print(f"   [Leonardo] OK → {output_path}")
                    return {
                        "success": True,
                        "image_path": output_path,
                        "prompt": prompt,
                        "url": img_url,
                        "platform": platform
                    }
            elif status == "FAILED":
                return {"success": False, "error": "Generation failed"}
            
            print(f"   [Leonardo] {status} ({(attempt+1)*5}с)...")
        
        return {"success": False, "error": "Timeout"}
    
    except Exception as e:
        print(f"   [Leonardo] Exception: {e}")
        return {"success": False, "error": str(e)}


def generate_image_for_post(post: dict, platform: str = "default") -> str | None:
    """
    Удобная обёртка — принимает dict поста, возвращает путь к изображению или None.
    Работает с любой структурой поста (text, caption, content).
    """
    text = (
        post.get("text") or
        post.get("caption") or
        post.get("content") or
        post.get("topic", "")
    )
    
    if not text:
        return None
    
    result = generate_image(text, platform=platform)
    return result.get("image_path") if result["success"] else None


if __name__ == "__main__":
    # Тест
    test_text = """🌴 Топ-3 места для зимовки в Таиланде

Паттайя, Чиангмай или Пхукет?
Каждый город — своя атмосфера и цены.
Расскажем где лучше для цифрового кочевника 👇"""
    
    print("Тест генерации изображения...")
    result = generate_image(test_text, platform="max", output_path="/tmp/test_auto.jpg")
    print(f"\nРезультат: {json.dumps(result, ensure_ascii=False, indent=2)}")
