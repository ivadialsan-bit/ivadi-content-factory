import json
import os
from datetime import datetime
import sys
sys.path.insert(0, "/root/factory")

from generate_post_carousel import generate_post_content
from generate_post_image import generate_flux_image
from publish_vk_content import publish_post_to_vk

def create_and_publish_post(pattern):
    """Pipeline: генерация контента -> Flux изображение -> VK публикация"""
    
    print("\n" + "="*70)
    print(f"ПОСТ: {pattern['Тема']}")
    print("="*70 + "\n")
    
    print("1. ГЕНЕРИРУЕМ КОНТЕНТ")
    post_content = generate_post_content(pattern)
    print(f"   OK - {len(post_content['caption'].split())} слов\n")
    
    print("2. ГЕНЕРИРУЕМ ИЗОБРАЖЕНИЕ (Flux)")
    output_dir = f"/root/factory/output/post_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)
    post_image_path = f"{output_dir}/image.jpg"
    
    img, path = generate_flux_image(post_content['image_description'], post_image_path)
    if img:
        print(f"   OK - Изображение готово\n")
    else:
        print(f"   ERROR - Flux недоступен\n")
        return None
    
    print("3. ПУБЛИКУЕМ НА VK")
    vk_url = publish_post_to_vk(post_content['caption'], post_image_path)
    
    if vk_url:
        print("\n" + "="*70)
        print("✅ ПОСТ ОПУБЛИКОВАН!")
        print("="*70)
        print(f"VK: {vk_url}\n")
    else:
        print("ERROR при публикации")
        return None
    
    return vk_url

if __name__ == "__main__":
    test_pattern = {
        "Тема": "Контроль vs гибкость",
        "Герои": "Орел и ласточка",
        "Вывод": "Сила в принятии, не в контроле",
        "Хук": "Что произойдет если ты потеряешь контроль?"
    }
    
    result = create_and_publish_post(test_pattern)
