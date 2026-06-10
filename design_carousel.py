import json
import anthropic
import sys
sys.path.insert(0, "/root/factory")
from config import CLAUDE_API_KEY

def design_carousel(carousel_content):
    """Дизайнер VK каруселей - анализирует контент и создаёт дизайн"""
    
    with open('/root/factory/carousel_designer_prompt.txt', 'r', encoding='utf-8') as f:
        designer_prompt = f.read()
    
    claude = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    
    prompt = designer_prompt + f"""

КОНТЕНТ ДЛЯ ДИЗАЙНА:
{json.dumps(carousel_content, ensure_ascii=False)}

Сейчас создай подробный дизайн этой карусели. Каждый слайд должен быть роскошным, минималистичным и психологически глубоким.

Помни:
- Слайд 1 = СТОП-КАДР, должен остановить лентой
- Каждый слайд читается за 2-3 сек
- Люксовые минималистичные детали (не перегруженно)
- Тёмная палитра, контраст
- Ответь ТОЛЬКО JSON без markdown
"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = msg.content[0].text.replace('```json', '').replace('```', '').strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Текст: {text[:200]}")
        
        # Если JSON сломан, возвращаем простой дефолтный дизайн
        return {
            "slides": [
                {"slide_number": i+1, "text": slide['text'], "text_size": "64px", "text_color": "#FFFFFF" if i % 2 == 0 else "#D4AF37", "background": {"type": "gradient", "colors": ["#0a0e1a", "#1a0a2e"]}, "luxury_details": []}
                for i, slide in enumerate(carousel_content['slides'])
            ],
            "carousel_strategy": "Default design",
            "cta": carousel_content.get('cta', '')
        }

if __name__ == "__main__":
    test_carousel = {
        "slides": [
            {"text": "Ты контролируешь жизнь?\nИли жизнь контролирует тебя?"},
            {"text": "Орел проверял всё:\nветер, крыло, силу"},
            {"text": "Пришел ураган.\nОрел сломал крыло."},
            {"text": "Ласточка не боялась.\nОна летела С ураганом."},
            {"text": "Сила не в контроле.\nСила в ГИБКОСТИ."}
        ],
        "cta": "Орел или ласточка? 🦅"
    }
    
    print("Проектируем карусель...")
    design = design_carousel(test_carousel)
    print(json.dumps(design, ensure_ascii=False, indent=2))
