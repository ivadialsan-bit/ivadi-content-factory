from PIL import Image, ImageDraw, ImageFont
import json
import os

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def apply_opacity(rgb, opacity):
    return rgb + (int(255 * opacity / 100),)

def render_carousel_slides(design_data, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    slide_paths = []
    
    for slide_data in design_data['slides']:
        slide_num = slide_data['slide_number']
        
        img = Image.new('RGB', (1080, 1350), (10, 10, 15))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        if slide_data['background']['type'] == 'gradient':
            colors = slide_data['background']['colors']
            rgb1 = hex_to_rgb(colors[0])
            rgb2 = hex_to_rgb(colors[1])
            
            for i in range(1080):
                for j in range(1350):
                    ratio = (i + j) / (1080 + 1350)
                    r = int(rgb1[0] + (rgb2[0] - rgb1[0]) * ratio)
                    g = int(rgb1[1] + (rgb2[1] - rgb1[1]) * ratio)
                    b = int(rgb1[2] + (rgb2[2] - rgb1[2]) * ratio)
                    draw.point((i, j), fill=(r, g, b))
        
        try:
            size = int(slide_data['text_size'].replace('px', ''))
            font_big = ImageFont.truetype("/root/factory/PlayfairDisplay-Bold.ttf", size)
            font_small = ImageFont.truetype("/root/factory/Roboto-Light.ttf", 32)
        except:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        for detail in slide_data.get('luxury_details', []):
            if 'линии' in detail.lower():
                gold_color = apply_opacity(hex_to_rgb('#D4AF37'), 30)
                draw.line([(60, 300), (1020, 300)], fill=gold_color, width=1)
                draw.line([(60, 1050), (1020, 1050)], fill=gold_color, width=1)
            
            if 'орнамент' in detail.lower():
                ornament_color = apply_opacity(hex_to_rgb('#D4AF37'), 3)
                draw.polygon([(60, 60), (100, 60), (80, 100)], outline=ornament_color)
                draw.polygon([(1020, 1290), (980, 1290), (1000, 1250)], outline=ornament_color)
        
        text = slide_data['text']
        text_color = slide_data.get('text_color', '#FFFFFF')
        text_rgb = hex_to_rgb(text_color)
        
        lines = text.split(chr(10))
        y_offset = 550
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_big)
            text_width = bbox[2] - bbox[0]
            x_pos = (1080 - text_width) // 2
            
            draw.text((x_pos, y_offset), line, fill=text_rgb, font=font_big)
            y_offset += 120
        
        slide_indicator = f"{slide_num}/{len(design_data['slides'])}"
        draw.text((50, 1280), slide_indicator, fill=apply_opacity(text_rgb, 50), font=font_small)
        
        path = f"{output_dir}/slide_{slide_num}.jpg"
        img.save(path, "JPEG", quality=95)
        slide_paths.append(path)
        
        print(f"   OK - Слайд {slide_num}")
    
    return slide_paths

if __name__ == "__main__":
    design = {
        "slides": [
            {"slide_number": 1, "text": "Ты контролируешь жизнь?", "text_size": "72px", "text_color": "#FFFFFF", "background": {"type": "gradient", "colors": ["#0a0e1a", "#1a0a2e"]}, "luxury_details": []},
            {"slide_number": 2, "text": "Орел проверял всё", "text_size": "64px", "text_color": "#D4AF37", "background": {"type": "gradient", "colors": ["#1a0a2e", "#2a1a4e"]}, "luxury_details": []},
            {"slide_number": 3, "text": "Пришел ураган", "text_size": "68px", "text_color": "#FF6B6B", "background": {"type": "gradient", "colors": ["#2a1a4e", "#1a0a2e"]}, "luxury_details": []},
            {"slide_number": 4, "text": "Ласточка летела с ураганом", "text_size": "60px", "text_color": "#A8E6CF", "background": {"type": "gradient", "colors": ["#1a0a2e", "#0a1a3e"]}, "luxury_details": []},
            {"slide_number": 5, "text": "Сила в ГИБКОСТИ", "text_size": "72px", "text_color": "#D4AF37", "background": {"type": "gradient", "colors": ["#0a0a15", "#1a0a2e"]}, "luxury_details": ["Две горизонтальные линии", "Орнамент"]}
        ]
    }
    
    print("Рендерим карусель...")
    paths = render_carousel_slides(design, "/tmp/carousel_test")
    print(f"Готово: {len(paths)} слайдов")
