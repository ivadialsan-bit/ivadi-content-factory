import json
import anthropic
import sys
sys.path.insert(0, "/root/factory")
from config import CLAUDE_API_KEY

THEMES = [
    "отношения",
    "карьера", 
    "страхи",
    "личные границы",
    "зависимости",
    "самооценка",
    "выбор",
    "маски"
]

def generate_pattern(theme):
    """Генерирует паттерн для темы"""
    
    claude = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    
    prompt = f"""Ты создаёшь паттерны для психологических постов про животных.

ТЕМА: {theme}

Создай один паттерн со следующими полями:
- Тема: суть психологической проблемы
- Герои: два животных (главный и антагонист или оба главные)
- Вывод: мораль истории в одной фразе
- Хук: провокационный вопрос для привлечения внимания

Требования:
- Герои должны быть разными животными (волк-лиса, орел-ласточка, и т.д.)
- Каждый герой отражает одну сторону конфликта
- Вывод должен быть практичным, не философским
- Хук должен провоцировать на клик (вопрос или неожиданное утверждение)

Ответ ТОЛЬКО JSON:
{{"тема": "...", "герои": "... и ...", "вывод": "...", "хук": "..."}}"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    
    text = msg.content[0].text.replace('```json', '').replace('```', '').strip()
    return json.loads(text)

def generate_all_patterns():
    """Генерирует паттерны для всех тем"""
    patterns = {}
    
    for theme in THEMES:
        print(f"Генерируем паттерн для '{theme}'...")
        pattern = generate_pattern(theme)
        patterns[theme] = pattern
        print(f"  OK - {pattern['герои']}\n")
    
    return patterns

if __name__ == "__main__":
    patterns = generate_all_patterns()
    print("\n" + "="*70)
    print("ВСЕ ПАТТЕРНЫ:")
    print("="*70)
    print(json.dumps(patterns, ensure_ascii=False, indent=2))
