import json
import anthropic
import gspread
from google.oauth2.service_account import Credentials
import sys
sys.path.insert(0, "/root/factory")
from config import CLAUDE_API_KEY

SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_ID = "1kB4F_zPEJKKJ-EcwKnrR_mS5-gVegyfDsAp7JR23F40"

def generate_post(script_data):
    """Генерирует пост (текст + 1 изображение) из сценария"""
    claude = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    
    prompt = "На основе этой психологической притчи создай ПОСТ для ВК.\n\n"
    prompt += f"СЦЕНАРИЙ:\n{script_data['script']}\n\n"
    prompt += f"МОРАЛЬ:\n{script_data['moral']}\n\n"
    prompt += """ТРЕБОВАНИЯ:

CAPTION (длинный текст к посту):
- Начни с КРЮЧКА (вопрос или провокация)
- Расскажи историю полностью (3-5 предложений)
- Добавь глубокий вывод (почему это важно)
- Закончи ВОПРОСОМ к аудитории или CTA
- Язык: эмоциональный, разговорный, вовлекающий
- Добавь эмодзи где уместно
- Длина: 300-500 слов (читается 2-3 минуты)

IMAGE DESCRIPTION (для Flux):
- Одна центральная сцена из истории
- Качественное, кинематографичное изображение
- Животные, эмоции, свет, атмосфера
- БЕЗ ТЕКСТА НА ИЗОБРАЖЕНИИ
- Тёмная, глубокая палитра

Ответ ТОЛЬКО JSON:
{"caption": "полный вовлекающий текст поста", "image_description": "для Flux - детальное описание", "cta": "финальный призыв"}"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text
    text = text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

def generate_carousel(script_data):
    """Генерирует карусель (4-5 слайдов) из сценария"""
    claude = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    
    prompt = "На основе этой психологической притчи создай КАРУСЕЛЬ для ВК (4-5 слайдов).\n\n"
    prompt += f"СЦЕНАРИЙ:\n{script_data['script']}\n\n"
    prompt += f"МОРАЛЬ:\n{script_data['moral']}\n\n"
    prompt += """СТРУКТУРА КАРУСЕЛИ:
- Слайд 1: КРЮЧОК (вопрос или провокация)
- Слайд 2-3: ИСТОРИЯ (по одному моменту)
- Слайд 4: МОРАЛЬ (вывод + вопрос)
- Слайд 5: ЭКШН (призыв)

ТРЕБОВАНИЯ:
- Каждый слайд: текст (1-2 строки) + описание изображения
- Текст КРУПНЫЙ, читается за 2-3 сек
- Эмоциональный, захватывающий

Ответ ТОЛЬКО JSON:
{"slides": [{"text": "текст", "image_description": "описание"}], "cta": "призыв"}"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text
    text = text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

if __name__ == "__main__":
    test_script = {
        "hook": "Что произойдет если я потеряю контроль?",
        "script": "Орел летел высоко. Каждый день проверял: ветер дует? Крыло целое? Сила есть? Однажды налетел ураган. Орел пробовал контролировать полет, но ураган сильнее. Орел сломал крыло. А рядом летела ласточка. Она не боялась ветра, она летела с ним. Ласточка в урагане осталась целой.",
        "moral": "Контроль дает иллюзию безопасности. Истинная сила в гибкости и принятии."
    }
    
    print("Генерируем пост...")
    post = generate_post(test_script)
    print(json.dumps(post, ensure_ascii=False, indent=2))
    
    print("\nГенерируем карусель...")
    carousel = generate_carousel(test_script)
    print(json.dumps(carousel, ensure_ascii=False, indent=2))
