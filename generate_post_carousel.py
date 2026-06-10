import json
import anthropic
import sys
sys.path.insert(0, "/root/factory")
from config import CLAUDE_API_KEY

def generate_post_content(pattern):
    """Генерирует ПОСТ - одна глубокая история"""
    claude = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    
    prompt = "Ты генерируешь ПСИХОЛОГИЧЕСКИЕ ПОСТЫ для ВК - глубокие истории через животных.\n\n"
    prompt += f"Тема: {pattern['Тема']}\n"
    prompt += f"Герои: {pattern['Герои']}\n"
    prompt += f"Вывод: {pattern['Вывод']}\n"
    prompt += f"Хук: {pattern['Хук']}\n\n"
    prompt += """ТРЕБОВАНИЯ К ПОСТУ:
- ИСТОРИЯ: полная, эмоциональная, вовлекающая
- CAPTION: 300-500 слов, начинается с крючка, заканчивается вопросом
- ИЗОБРАЖЕНИЕ: одна сильная сцена (животные, эмоции, качество Flux)
- БЕЗ ТЕКСТА НА ИЗОБРАЖЕНИИ
- Язык: простой, разговорный, психологически глубокий

СТРУКТУРА:
1. Крючок (1 фраза)
2. История (3-4 абзаца)
3. Вывод (1-2 абзаца)
4. CTA (вопрос)

Ответ ТОЛЬКО JSON: {"caption": "текст", "image_description": "описание", "cta": "вопрос"}"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

def generate_carousel_content(pattern):
    """Генерирует КАРУСЕЛЬ - другая история или другой угол"""
    claude = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    
    prompt = "Ты генерируешь ПСИХОЛОГИЧЕСКИЕ КАРУСЕЛИ для ВК (5-6 слайдов).\n\n"
    prompt += f"Тема: {pattern['Тема']}\n"
    prompt += f"Герои: {pattern['Герои']}\n"
    prompt += f"Вывод: {pattern['Вывод']}\n"
    prompt += f"Хук: {pattern['Хук']}\n\n"
    prompt += """ГЛАВНОЕ: Это НЕ пост, это КАРУСЕЛЬ. Другой угол, другая история, но ТА ЖЕ ТЕМА.

ТРЕБОВАНИЯ:
- СЛАЙДЫ: 5-6 штук с крупным текстом
- ТЕКСТ: читается за 2-3 сек на слайде
- СТРУКТУРА: крючок -> история пошагово -> вывод -> вопрос
- ЯЗЫК: простой, ударный, эмоциональный
- МАКСИМУМ ВОВЛЕЧЕНИЯ

Ответ ТОЛЬКО JSON: {"slides": [{"text": "текст"}], "cta": "призыв"}"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

if __name__ == "__main__":
    test_pattern = {
        "Тема": "Контроль vs гибкость",
        "Герои": "Орел и ласточка",
        "Вывод": "Сила в принятии, не в контроле",
        "Хук": "Что произойдет если ты потеряешь контроль?"
    }
    
    print("=== ГЕНЕРИРУЕМ ПОСТ ===")
    post = generate_post_content(test_pattern)
    print(json.dumps(post, ensure_ascii=False, indent=2))
    
    print("\n=== ГЕНЕРИРУЕМ КАРУСЕЛЬ ===")
    carousel = generate_carousel_content(test_pattern)
    print(json.dumps(carousel, ensure_ascii=False, indent=2))
