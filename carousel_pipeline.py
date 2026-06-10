import json
import os
from datetime import datetime
import sys
sys.path.insert(0, "/root/factory")

from generate_post_carousel import generate_carousel_content
from design_carousel import design_carousel
from render_carousel import render_carousel_slides
from publish_vk_content import publish_carousel_to_vk

def create_and_publish_carousel(pattern):
    """Pipeline: генерация -> дизайн -> рендеринг -> VK публикация"""
    
    print("\n" + "="*70)
    print(f"КАРУСЕЛЬ: {pattern['Тема']}")
    print("="*70 + "\n")
    
    print("1. ГЕНЕРИРУЕМ КОНТЕНТ")
    print("-" * 70)
    carousel_content = generate_carousel_content(pattern)
    print(f"   OK - {len(carousel_content['slides'])} слайдов")
    
    print("\n2. ПРОЕКТИРУЕМ ДИЗАЙН")
    print("-" * 70)
    design_data = design_carousel(carousel_content)
    print(f"   OK - Дизайн готов")
    
    print("\n3. РЕНДЕРИМ СЛАЙДЫ")
    print("-" * 70)
    output_dir = f"/root/factory/output/carousel_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    slide_paths = render_carousel_slides(design_data, output_dir)
    print(f"   OK - Слайды в {output_dir}")
    
    print("\n4. ПУБЛИКУЕМ НА VK")
    print("-" * 70)
    vk_url = publish_carousel_to_vk(slide_paths, carousel_content['cta'])
    
    print("\n" + "="*70)
    print("✅ КАРУСЕЛЬ ОПУБЛИКОВАНА!")
    print("="*70)
    print(f"Слайды: {output_dir}")
    print(f"VK: {vk_url}")
    print("="*70 + "\n")
    
    return {
        "content": carousel_content,
        "design": design_data,
        "slides": slide_paths,
        "output_dir": output_dir,
        "vk_url": vk_url
    }

if __name__ == "__main__":
    test_pattern = {
        "Тема": "Контроль vs гибкость",
        "Герои": "Орел и ласточка",
        "Вывод": "Сила в принятии, не в контроле",
        "Хук": "Что произойдет если ты потеряешь контроль?"
    }
    
    result = create_and_publish_carousel(test_pattern)
