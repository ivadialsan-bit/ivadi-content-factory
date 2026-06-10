import sys
import os
sys.path.insert(0, '/root/factory')

from generate_post_only import generate_post_content
from generate_post_image import generate_flux_image
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv('/root/factory/.ivadi.env')

OUTPUT_DIR = '/root/factory/output/ivadi'
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_post_with_image(topic: str, post_type: str = 'lifehack',
                              direction: str = 'travel', style: str = None) -> dict:
    """
    Генерирует пост с картинкой для MAX/ВК/Instagram
    Возвращает: текст поста + путь к картинке
    """
    print(f"[1/3] Генерирую текст поста...")

    # Генерируем текст через существующий генератор
    content = generate_post_content(topic)
    caption = content.get('caption', '')
    image_description = content.get('image_description', '')

    print(f"[2/3] Генерирую изображение...")

    # Усиливаем промпт для изображения
    base_style = style or "cinematic travel photography, golden hour lighting, ultra realistic, 4k"
    
    flux_prompt = (
        f"{image_description}. "
        f"Style: {base_style}. "
        f"No text, no watermarks, professional quality."
    )

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    img_path = f"{OUTPUT_DIR}/post_{timestamp}.jpg"

    img, saved_path = generate_flux_image(flux_prompt, img_path)

    print(f"[3/3] Готово")

    return {
        'caption': caption,
        'cta': content.get('cta', ''),
        'image_path': saved_path,
        'image_prompt': flux_prompt,
        'topic': topic,
        'type': post_type,
        'created_at': datetime.now().isoformat()
    }


if __name__ == '__main__':
    topic = sys.argv[1] if len(sys.argv) > 1 else 'Топ 3 лайфхака для путешественников'
    result = generate_post_with_image(topic)
    print(f"\nТекст: {result['caption'][:100]}...")
    print(f"Картинка: {result['image_path']}")
    print(f"CTA: {result['cta']}")
