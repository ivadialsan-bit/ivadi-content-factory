import json
from datetime import datetime
import sys
sys.path.insert(0, "/root/factory")

from generate_post_carousel import generate_post_content, generate_carousel_content
from save_content import save_to_sheets
from PIL import Image, ImageDraw, ImageFont
import os

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

def save_carousel_slides(slides, output_dir, hook_title):
    """Сохраняет слайды"""
    os.makedirs(output_dir, exist_ok=True)
    
    paths = []
    for i, slide in enumerate(slides):
        path = f"{output_dir}/carousel_slide_{i+1}.jpg"
        slide.save(path, "JPEG", quality=95)
        paths.append(path)
    
    print(f"   OK - {len(slides)} слайдов сохранено")
    return paths

def create_content_from_pattern(pattern):
    """Полный цикл"""
    
    print("\n" + "="*60)
    print(f"ПАТТЕРН: {pattern['Тема']}")
    print("="*60 + "\n")
    
    print("1. Генерируем ПОСТ...")
    post_data = generate_post_content(pattern)
    print(f"   OK - {len(post_data['caption'].split())} слов")
    
    print("\n2. Генерируем КАРУСЕЛЬ...")
    carousel_data = generate_carousel_content(pattern)
    print(f"   OK - {len(carousel_data['slides'])} слайдов")
    
    print("\n3. Сохраняем в Sheets...")
    save_to_sheets(post_data, carousel_data, pattern)
    
    print("\n4. Создаём изображения карусели...")
    carousel_slides = create_carousel_slides(carousel_data)
    output_dir = f"/root/factory/output/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    carousel_paths = save_carousel_slides(carousel_slides, output_dir, pattern['Хук'][:30])
    
    print("\n" + "="*60)
    print("ГОТОВО!")
    print("="*60)
    print(f"Карусель: {len(carousel_paths)} слайдов")
    print("="*60 + "\n")
    
    return {
        "post": post_data,
        "carousel": carousel_data,
        "carousel_images": carousel_paths
    }

if __name__ == "__main__":
    test_pattern = {
        "Тема": "Контроль vs гибкость",
        "Герои": "Орел и ласточка",
        "Вывод": "Сила в принятии, не в контроле",
        "Хук": "Что произойдет если ты потеряешь контроль?"
    }
    
    result = create_content_from_pattern(test_pattern)
