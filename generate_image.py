import os
from PIL import Image, ImageDraw, ImageFont

FONT_BODY = "/root/factory/Roboto-Light.ttf"

def generate_images_parallel(scenes, output_dir):
    results = []
    for i, scene_text in enumerate(scenes):
        W, H = 1080, 1920
        img = Image.new("RGB", (W, H), "#0D0D0D")
        draw = ImageDraw.Draw(img)
        for y in range(H):
            ratio = y / H
            d = int(13 + 12 * ratio)
            draw.line([(0, y), (W, y)], fill=(d, d, d + 8))
        draw.rectangle([30, 30, 1050, 1890], outline="#C9A84C", width=1)
        try:
            f_body = ImageFont.truetype(FONT_BODY, 42)
        except:
            f_body = ImageFont.load_default()
        words = scene_text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=f_body)
            if bbox[2] - bbox[0] <= 860:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        line_h = 60
        total_h = len(lines) * line_h
        start_y = 960 - total_h // 2
        for line in lines:
            draw.text((540, start_y), line, fill="#FFFFFF", anchor="mm", font=f_body)
            start_y += line_h
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"scene_{i}.jpg")
        img.save(output_path)
        results.append(output_path)
        print(f"[IMAGE] Scene {i} saved")
    return results
