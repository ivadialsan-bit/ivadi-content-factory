import requests
import io
from PIL import Image

HF_TOKEN = "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"

def generate_hf_image(description, output_path=None):
    """Генерирует изображение через Hugging Face Stable Diffusion"""
    
    print(f"   Генерируем Stable Diffusion изображение...")
    
    # Оптимизируем промпт
    hf_prompt = f"""Cinematic dramatic photorealistic painting:
{description}

Style: dark moody cinematography, professional oil painting, 8k quality, masterpiece
No text"""
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    payload = {
        "inputs": hf_prompt,
        "parameters": {
            "negative_prompt": "blurry, low quality, text, watermark",
            "num_inference_steps": 50,
            "guidance_scale": 7.5
        }
    }
    
    for attempt in range(3):
        try:
            response = requests.post(
                "https://huggingface-proxy.ivadialsan.workers.dev/",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                
                # Resize для VK
                img = img.resize((1080, 1350), Image.Resampling.LANCZOS)
                
                if output_path:
                    img.save(output_path, "JPEG", quality=95)
                
                print(f"   OK - Stable Diffusion готово")
                return img, output_path
            else:
                error_msg = response.text
                if attempt < 2:
                    print(f"   Повтор {attempt+1}/3...")
                    continue
                else:
                    print(f"   ERROR: {error_msg[:100]}")
                    
        except Exception as e:
            if attempt < 2:
                print(f"   Повтор {attempt+1}/3...")
                continue
            else:
                print(f"   ERROR: {str(e)[:100]}")
    
    return None, None
