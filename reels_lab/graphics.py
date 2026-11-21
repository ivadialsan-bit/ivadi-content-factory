"""Self-contained kinetic motion graphics (no stock footage or generated images)."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

DARK = (9, 18, 28)
MINT = (178, 245, 216)
WHITE = (244, 246, 244)
MUTED = (165, 181, 188)
ACCENT = (245, 187, 112)


def font_path(explicit=None):
    paths = [
        explicit,
        str(Path(__file__).parent / "Montserrat-ExtraBold.ttf"),
        "C:/Windows/Fonts/Montserrat-ExtraBold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for candidate in paths:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise RuntimeError("No usable Unicode font. Supply --font with a licensed font path.")


def ease(t):
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def _text(draw, xy, content, font, fill=WHITE, anchor=None):
    draw.text(xy, content, font=font, fill=fill, anchor=anchor,
              stroke_width=0)


def frame(schedule, seconds, width=1080, height=1920, font_file=None):
    scale = width / 1080
    scene = schedule["scenes"][-1]
    for entry in schedule["scenes"]:
        if seconds < entry["start"] + entry["duration"]:
            scene = entry
            break
    local = max(0.0, seconds - scene["start"])
    entrance = ease((local - 0.05) / 0.65)
    image = Image.new("RGB", (width, height), DARK)
    d = ImageDraw.Draw(image)
    p = lambda n: round(n * scale)
    heavy = font_path(font_file)
    large = ImageFont.truetype(heavy, p(76))
    medium = ImageFont.truetype(heavy, p(43))
    small = ImageFont.truetype(heavy, p(28))
    huge = ImageFont.truetype(heavy, p(148))
    margin = p(84)
    # Procedural orbit lines and subtle focal shapes, deterministic at any timestamp.
    for i in range(6):
        radius = p(180 + 110 * i)
        cx = width // 2 + p(340)
        cy = p(690)
        d.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                  outline=(18 + i * 3, 36 + i * 4, 44 + i * 3), width=max(1, p(2)))
    d.rectangle((margin, p(122), width - margin, p(125)), fill=MINT)
    _text(d, (margin, p(81)), "AI / WORKFLOW", small, MINT)
    # Title moves into its settled position; no jarring wipes or glitch effects.
    base_y = p(260 + 48 * (1 - entrance))
    headline = scene["headline"]
    chunks = []
    if headline == "30 РАБОЧИХ ПРОМПТОВ":
        chunks = ["30 РАБОЧИХ", "ПРОМПТОВ"]
    elif headline == "ПОСМОТРИ РАЗНИЦУ":
        chunks = ["ПОСМОТРИ", "РАЗНИЦУ"]
    elif headline == "ДОБАВЬ В ЗАПРОС":
        chunks = ["ДОБАВЬ", "В ЗАПРОС"]
    else:
        chunks = ["ИИ ПИШЕТ", "ВОДУ?"]
    for ix, part in enumerate(chunks):
        _text(d, (margin, base_y + p(ix * 112)), part, large,
              MINT if ix == len(chunks)-1 else WHITE)
    top = p(645)
    left, right = margin, width - margin
    box_h = p(715)
    d.rounded_rectangle((left, top, right, top + box_h), radius=p(35),
                        fill=(20, 34, 44), outline=(45, 75, 79), width=p(3))
    kind = scene["type"]
    if kind == "hook":
        _text(d, (left+p(55), top+p(70)), "ОБЫЧНЫЙ ОТВЕТ ИИ", medium, MUTED)
        for k, short in enumerate((0.88, 0.76, 0.94, 0.48)):
            yy = top + p(190+95*k)
            d.rounded_rectangle((left+p(55), yy, left+p(55+800*short), yy+p(22)),
                                radius=p(9), fill=(78, 101, 107))
        _text(d, (left+p(55), top+p(580)), "Много слов. Мало пользы.", medium, ACCENT)
    elif kind == "prompt":
        _text(d, (left+p(55), top+p(70)), "ВСТАВЬ В КОНЕЦ ЗАПРОСА", small, MUTED)
        phrases = ["3 КОНКРЕТНЫХ ШАГА", "1 ПРИМЕР", "БЕЗ ВСТУПЛЕНИЯ"]
        count = min(3, max(0, int((local - 0.12) / 0.85) + 1))
        for k in range(count):
            yy = top + p(190 + 145*k)
            d.rounded_rectangle((left+p(45), yy-p(19), right-p(45), yy+p(91)),
                                radius=p(22), fill=(35, 65, 65))
            _text(d, (left+p(80), yy+p(10)), phrases[k], medium, WHITE)
    elif kind == "result":
        d.rounded_rectangle((left+p(43), top+p(90), right-p(43), top+p(315)),
                            radius=p(25), fill=(62, 52, 48))
        _text(d, (left+p(72), top+p(127)), "БЫЛО", medium, ACCENT)
        _text(d, (left+p(72), top+p(220)), "Общие рекомендации", small)
        d.rounded_rectangle((left+p(43), top+p(359), right-p(43), top+p(626)),
                            radius=p(25), fill=(33, 77, 65))
        _text(d, (left+p(72), top+p(395)), "СТАЛО", medium, MINT)
        _text(d, (left+p(72), top+p(493)), "3 шага + пример", medium)
    else:
        _text(d, (left+p(55), top+p(95)), "НАБОР ПРАКТИЧЕСКИХ", small, MUTED)
        _text(d, (left+p(55), top+p(208)), "30", huge, MINT)
        _text(d, (left+p(370), top+p(300)), "ПРОМПТОВ", medium, WHITE)
        _text(d, (left+p(55), top+p(492)), "890 ₽", huge, WHITE)
        _text(d, (left+p(55), top+p(640)), "Тест предложения, не продажа", small, MUTED)
    _text(d, (margin, p(1546)), scene["label"], small, WHITE)
    d.rectangle((margin, p(1701), width - margin, p(1704)), fill=(49, 77, 80))
    progress = min(1.0, seconds / schedule["duration"])
    d.rectangle((margin, p(1701), margin + round((width - 2*margin) * progress),
                 p(1704)), fill=MINT)
    _text(d, (margin, p(1757)), "СОХРАНИ • ПРИМЕНИ • ПРОВЕРЬ", small, MUTED)
    return image
