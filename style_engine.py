from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1080, 1080
FONTS = {
    'serif_bold': '/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf',
    'serif': '/usr/share/fonts/truetype/freefont/FreeSerif.ttf',
    'sans_bold': '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    'sans': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
}

def get_font(name, size):
    return ImageFont.truetype(FONTS[name], size)

def draw_text_wrapped(draw, text, font, fill, max_width, x, y, anchor='mm'):
    words = text.split()
    lines = []
    current = ''
    for word in words:
        test = f'{current} {word}'.strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    line_height = get_font('serif', font.size).getbbox('A')[3] + 10
    total_height = len(lines) * line_height
    start_y = y - total_height // 2
    for line in lines:
        draw.text((x, start_y), line, fill=fill, anchor='mm', font=font)
        start_y += line_height
    return start_y

# СТИЛЬ А — Люкс (тёмный + золото + serif)
def style_luxury(title, subtitle, body, tag, slide_num, total):
    img = Image.new('RGB', (W, H), '#0D0D0D')
    draw = ImageDraw.Draw(img)
    for y in range(H):
        ratio = y / H
        d = int(13 + 8 * ratio)
        draw.line([(0, y), (W, y)], fill=(d, d, d + 5))
    draw.rectangle([30, 30, 1050, 1050], outline='#C9A84C', width=1)
    draw.rectangle([80, 80, 1000, 82], fill='#C9A84C')
    draw.rectangle([80, 998, 1000, 1000], fill='#C9A84C')
    f_tag = get_font('serif', 24)
    f_num = get_font('serif', 22)
    f_title = get_font('serif_bold', 82)
    f_sub = get_font('serif', 38)
    f_body = get_font('serif', 34)
    draw.text((540, 130), tag.upper(), fill='#C9A84C', anchor='mm', font=f_tag)
    draw.text((960, 130), f'{slide_num}/{total}', fill='#444444', anchor='mm', font=f_num)
    draw.text((540, 350), title, fill='#FFFFFF', anchor='mm', font=f_title)
    draw.text((540, 460), '◆', fill='#C9A84C', anchor='mm', font=f_sub)
    draw_text_wrapped(draw, body, f_body, '#AAAAAA', 860, 540, 580)
    if slide_num < total:
        draw.text((960, 970), '→', fill='#C9A84C', anchor='mm', font=f_sub)
    draw.text((540, 1040), '@myshlenie_bogatyh', fill='#444444', anchor='mm', font=f_num)
    return img

# СТИЛЬ Б — Рукопись (бежевый + рукописный feel)
def style_manuscript(title, subtitle, body, tag, slide_num, total):
    img = Image.new('RGB', (W, H), '#F5F0E8')
    draw = ImageDraw.Draw(img)
    for i in range(0, H, 48):
        draw.line([(60, i), (1020, i)], fill='#E8E0D0', width=1)
    draw.rectangle([60, 60, 1020, 1020], outline='#8B6914', width=2)
    f_title = get_font('serif_bold', 78)
    f_body = get_font('serif', 36)
    f_tag = get_font('serif', 24)
    f_num = get_font('serif', 22)
    draw.text((540, 200), tag, fill='#8B6914', anchor='mm', font=f_tag)
    draw.line([(150, 230), (930, 230)], fill='#8B6914', width=1)
    draw.text((540, 370), title, fill='#1A1A1A', anchor='mm', font=f_title)
    draw.line([(300, 440), (780, 440)], fill='#C9A84C', width=2)
    draw_text_wrapped(draw, body, f_body, '#333333', 820, 540, 600)
    if slide_num < total:
        draw.text((900, 960), '→', fill='#8B6914', anchor='mm', font=f_body)
    draw.text((540, 1020), f'@myshlenie_bogatyh  •  {slide_num}/{total}', fill='#999999', anchor='mm', font=f_tag)
    return img

# СТИЛЬ В — Минимализм (белый + чёрный + золотая деталь)
def style_minimal(title, subtitle, body, tag, slide_num, total):
    img = Image.new('RGB', (W, H), '#FAFAFA')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 8, H], fill='#C9A84C')
    draw.rectangle([0, 0, W, 8], fill='#C9A84C')
    f_title = get_font('sans_bold', 76)
    f_body = get_font('sans', 36)
    f_tag = get_font('sans', 24)
    f_num = get_font('sans', 22)
    draw.text((100, 160), tag.upper(), fill='#C9A84C', anchor='lm', font=f_tag)
    draw.text((100, 380), title, fill='#111111', anchor='lm', font=f_title)
    draw.rectangle([100, 430, 400, 434], fill='#C9A84C')
    draw_text_wrapped(draw, body, f_body, '#555555', 860, 540, 620)
    if slide_num < total:
        draw.text((960, 960), '→', fill='#C9A84C', anchor='mm', font=f_body)
    draw.text((100, 1020), f'@myshlenie_bogatyh', fill='#BBBBBB', anchor='lm', font=f_num)
    draw.text((980, 1020), f'{slide_num}/{total}', fill='#BBBBBB', anchor='rm', font=f_num)
    return img

# СТИЛЬ Г — Дерзкий (тёмный + красный акцент)
def style_bold(title, subtitle, body, tag, slide_num, total):
    img = Image.new('RGB', (W, H), '#111111')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 12], fill='#C0392B')
    draw.rectangle([0, H-12, W, H], fill='#C0392B')
    f_title = get_font('sans_bold', 88)
    f_body = get_font('sans', 36)
    f_tag = get_font('sans', 26)
    f_num = get_font('sans', 22)
    draw.text((540, 180), tag.upper(), fill='#C0392B', anchor='mm', font=f_tag)
    draw.text((540, 400), title, fill='#FFFFFF', anchor='mm', font=f_title)
    draw.rectangle([200, 460, 880, 464], fill='#C0392B')
    draw_text_wrapped(draw, body, f_body, '#CCCCCC', 840, 540, 620)
    if slide_num < total:
        draw.text((960, 960), '→', fill='#C0392B', anchor='mm', font=f_body)
    draw.text((540, 1030), f'@myshlenie_bogatyh  {slide_num}/{total}', fill='#444444', anchor='mm', font=f_num)
    return img

# СТИЛЬ Д — Тетрадь (клетка + синяя ручка)
def style_notebook(title, subtitle, body, tag, slide_num, total):
    img = Image.new('RGB', (W, H), '#FEFEFE')
    draw = ImageDraw.Draw(img)
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill='#E8EEF8', width=1)
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill='#E8EEF8', width=1)
    draw.rectangle([120, 0, 124, H], fill='#FFB3B3')
    f_title = get_font('serif_bold', 76)
    f_body = get_font('serif', 36)
    f_tag = get_font('serif', 26)
    f_num = get_font('serif', 22)
    draw.text((540, 180), tag, fill='#2255AA', anchor='mm', font=f_tag)
    draw.line([(150, 220), (930, 221)], fill='#2255AA', width=2)
    draw.text((540, 380), title, fill='#1A1A2E', anchor='mm', font=f_title)
    draw_text_wrapped(draw, body, f_body, '#2255AA', 780, 540, 580)
    if slide_num < total:
        draw.text((960, 960), '→', fill='#2255AA', anchor='mm', font=f_body)
    draw.text((540, 1030), f'@myshlenie_bogatyh  •  {slide_num}/{total}', fill='#AAAAAA', anchor='mm', font=f_num)
    return img

STYLES = {
    'luxury': style_luxury,
    'manuscript': style_manuscript,
    'minimal': style_minimal,
    'bold': style_bold,
    'notebook': style_notebook,
}

def create_slide(style, title, subtitle, body, tag, slide_num, total, output_path):
    func = STYLES.get(style, style_luxury)
    img = func(title, subtitle, body, tag, slide_num, total)
    img.save(output_path, quality=95)
    return output_path

if __name__ == '__main__':
    os.makedirs('/root/factory/test_styles', exist_ok=True)
    test_data = {
        'title': 'Богатые думают иначе',
        'subtitle': 'Главный секрет',
        'body': '93% людей никогда не достигнут финансовой свободы. Причина не в деньгах — в мышлении.',
        'tag': 'Мышление богатых',
    }
    for style_name in STYLES:
        path = f'/root/factory/test_styles/{style_name}.png'
        create_slide(style_name, test_data['title'], test_data['subtitle'],
                    test_data['body'], test_data['tag'], 1, 8, path)
        print(f'✅ {style_name}: {path}')
    print('Все стили готовы')
