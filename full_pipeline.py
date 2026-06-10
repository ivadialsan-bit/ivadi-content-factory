import json
import os
from datetime import datetime
import sys
sys.path.insert(0, "/root/factory")

from generate_post_carousel import generate_post_content, generate_carousel_content
from save_content import save_to_sheets
from generate_post_image import generate_flux_image
from upload_content import upload_carousel_to_drive, upload_post_image_to_drive
from publish_vk_content import publish_post_to_vk, publish_carousel_to_vk
from PIL import Image, ImageDraw, ImageFont

def create_carousel_slides(carousel_data):
    """Создаёт слайды карусели"""
    slides = []
    colors = [(15, 23, 42), (20, 25, 40), (25, 20, 35), (18, 22, 38), (22, 18, 32)]
    
    for i, slide in enumerate(carousel_data['slides']):
        img = Image.new('RGB', (1080, 1350), colors[i % len(colors)])
        draw = ImageDraw.Draw(img, 'RGBA')
        
        for x in range(1080):
            alpha = int((x / 1080) * 100)
            draw.line([(x, 0), (x, 1350)], fill=(255, 255, 255, int(alpha * 0.3)))
        
        try:
            font = ImageFont.truetype("/root/factory/PlayfairDisplay-Bold.ttf", 60)
        except:
            font = ImageFont.load_default()
        
        draw = ImageDraw.Draw(img)
        text = slide['text']
        lines = text.split(chr(10))
        y_offset = 400
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x_pos = (1080 - text_width) // 2
            draw.text((x_pos, y_offset), line, fill=(255, 255, 255), font=font)
            y_offset += 120
        
        slides.append(img)
    
    return slides

def save_carousel_slides_local(slides, output_dir, hook_title):
    """Сохраняет слайды локально"""
    os.makedirs(output_dir, exist_ok=True)
    
    paths = []
    for i, slide in enumerate(slides):
        path = f"{output_dir}/carousel_slide_{i+1}.jpg"
        slide.save(path, "JPEG", quality=95)
        paths.append(path)
    
    return paths

def full_content_pipeline(pattern, publish_now=False):
    """Полный pipeline: генерация -> загрузка -> публикация"""
    
    print("\n" + "="*70)
    print(f"ТЕМА: {pattern['Тема']}")
    print("="*70 + "\n")
    
    # 1. Генерируем пост и карусель
    print("1. ГЕНЕРИРУЕМ КОНТЕНТ")
    print("-" * 70)
    
    print("   Пост...")
    post_data = generate_post_content(pattern)
    print(f"   OK - {len(post_data['caption'].split())} слов")
    
    print("   Карусель...")
    carousel_data = generate_carousel_content(pattern)
    print(f"   OK - {len(carousel_data['slides'])} слайдов")
    
    # 2. Сохраняем в Sheets
    print("\n2. СОХРАНЯЕМ В SHEETS")
    print("-" * 70)
    save_to_sheets(post_data, carousel_data, pattern)
    
    # 3. Создаём изображения
    print("\n3. СОЗДАЁМ ИЗОБРАЖЕНИЯ")
    print("-" * 70)
    
    output_dir = f"/root/factory/output/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("   Карусель слайды...")
    carousel_slides = create_carousel_slides(carousel_data)
    carousel_paths = save_carousel_slides_local(carousel_slides, output_dir, pattern['Хук'][:30])
    print(f"   OK - {len(carousel_paths)} слайдов")
    
    print("   Пост изображение (Flux)...")
    post_image_path = f"{output_dir}/post_image.jpg"
    post_img, _ = generate_flux_image(post_data['image_description'], post_image_path)
    if post_img:
        print(f"   OK - Flux готово")
    else:
        print(f"   SKIPPED - Flux недоступен")
    
    # 4. Загружаем на Drive
    print("\n4. ЗАГРУЖАЕМ НА GOOGLE DRIVE")
    print("-" * 70)
    
    print("   Карусель...")
    upload_carousel_to_drive(carousel_paths, post_data, carousel_data)
    
    if post_img:
        print("   Пост изображение...")
        upload_post_image_to_drive(post_image_path, post_data)
    
    # 5. Публикуем на VK (если флаг publish_now=True)
    if publish_now:
        print("\n5. ПУБЛИКУЕМ НА VK")
        print("-" * 70)
        
        print("   Пост...")
        if post_img:
            post_vk_url = publish_post_to_vk(post_data['caption'], post_image_path)
        
        print("   Карусель...")
        carousel_vk_url = publish_carousel_to_vk(carousel_paths, carousel_data['cta'])
    
    print("\n" + "="*70)
    print("ГОТОВО!")
    print("="*70 + "\n")
    
    return {
        "post": post_data,
        "carousel": carousel_data,
        "carousel_images": carousel_paths,
        "post_image": post_image_path if post_img else None
    }

if __name__ == "__main__":
    test_pattern = {
        "Тема": "Контроль vs гибкость",
        "Герои": "Орел и ласточка",
        "Вывод": "Сила в принятии, не в контроле",
        "Хук": "Что произойдет если ты потеряешь контроль?"
    }
    
    result = full_content_pipeline(test_pattern, publish_now=False)
