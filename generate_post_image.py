import requests
import io
import time
from PIL import Image

LEONARDO_API_KEY = "d42c2467-3d55-43b4-8ce7-fa760ffba0c6"
LEONARDO_MODEL_ID = "b24e16ff-06e3-43eb-8d33-4416c2d75876"  # Leonardo Phoenix

def generate_flux_image(description, output_path=None):
    """Генерирует изображение через Leonardo AI"""
    
    print(f"   Генерируем изображение через Leonardo AI...")
    print(f"   Промпт: {description[:100]}...")
    
    headers = {
        "Authorization": f"Bearer {LEONARDO_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": description,
        "modelId": LEONARDO_MODEL_ID,
        "width": 1280,
        "height": 720,
        "num_images": 1,
        "guidance_scale": 7,
        "photoReal": False,
        "alchemy": True
    }
    
    try:
        # Запускаем генерацию
        r = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/generations",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if r.status_code != 200:
            print(f"   ERROR запуска: {r.status_code} {r.text[:200]}")
            return None, None
        
        generation_id = r.json()["sdGenerationJob"]["generationId"]
        print(f"   ID генерации: {generation_id}, ждём результат...")
        
        # Поллинг результата
        for attempt in range(24):  # до 120 сек
            time.sleep(5)
            r2 = requests.get(
                f"https://cloud.leonardo.ai/api/rest/v1/generations/{generation_id}",
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
                    img_response = requests.get(img_url, timeout=30)
                    img = Image.open(io.BytesIO(img_response.content))
                    
                    if output_path:
                        img.save(output_path, "JPEG", quality=95)
                    
                    print(f"   OK - изображение готово")
                    return img, output_path
                    
            elif status == "FAILED":
                print(f"   ERROR: генерация завершилась с ошибкой")
                return None, None
                
            print(f"   Статус: {status}, ждём... ({(attempt+1)*5}с)")
        
        print(f"   ERROR: таймаут ожидания")
        return None, None
        
    except Exception as e:
        print(f"   ERROR: {e}")
        return None, None
