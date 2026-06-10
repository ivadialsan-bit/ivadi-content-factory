import requests
import io
from PIL import Image
import os

# Жёсткий ключ OpenAI
OPENAI_API_KEY = "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"

def generate_dalle_image(description, output_path=None):
    """Генерирует изображение через DALL-E"""
    
    print(f"   Генерируем DALL-E изображение...")
    
    # Оптимизируем промпт для DALL-E
    dalle_prompt = f"""Create a cinematic, dramatic, photorealistic oil painting style image:
{description}

Style: dark dramatic cinematography, moody lighting, professional art, 8k quality, masterpiece
No text on image"""
    
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "dall-e-2",
        "prompt": dalle_prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "standard"
    }
    
    try:
        response = requests.post(
            "https://dalle-proxy.ivadialsan.workers.dev/",
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            data = response.json()
            if "data" in data and data["data"]:
                img_url = data["data"][0]["url"]
                img_response = requests.get(img_url, timeout=30)
                img = Image.open(io.BytesIO(img_response.content))
                
                # Resizing to 1080x1350 for VK
                img = img.resize((1080, 1350), Image.Resampling.LANCZOS)
                
                if output_path:
                    img.save(output_path, "JPEG", quality=95)
                
                print(f"   OK - DALL-E готово")
                return img, output_path
        else:
            error = response.json()
            print(f"   ERROR: {error.get('error', {}).get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ERROR DALL-E: {e}")
    
    return None, None
