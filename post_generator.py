import json
import random
import anthropic
import sys
sys.path.insert(0, "/root/factory")
from generate_post_only import generate_post_content
from generate_post_image import generate_flux_image
from publish_vk_content import publish_post_to_vk
import os
from datetime import datetime

CLAUDE_KEY = "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"

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

# Предзаготовленные паттерны (резервный вариант если Claude не работает)
DEFAULT_PATTERNS = {
    "отношения": {"theme": "Волк и волчица", "heroes": "Волк и Волчица", "conclusion": "Любовь требует честности", "hook": "Когда ты последний раз говорил правду своему партнёру?"},
    "карьера": {"theme": "Муравей и кузнечик", "heroes": "Муравей и Кузнечик", "conclusion": "Работа ради смысла важнее денег", "hook": "Работаешь ли ты для жизни или живёшь для работы?"},
    "страхи": {"theme": "Кролик в лесу", "heroes": "Кролик и Лиса", "conclusion": "Страх растёт в темноте одиночества", "hook": "Какой страх ты носишь один?"},
    "личные границы": {"theme": "Кошка и собака", "heroes": "Кошка и Собака", "conclusion": "Границы — это любовь к себе", "hook": "Знаешь ли ты своё \"нет\"?"},
    "зависимости": {"theme": "Рыба в аквариуме", "heroes": "Рыба и Паук", "conclusion": "Зависимость — потеря свободы выбора", "hook": "От чего ты зависишь больше всего?"},
    "самооценка": {"theme": "Воробей и орёл", "heroes": "Воробей и Орёл", "conclusion": "Стоимость определяешь ты, не другие", "hook": "Почему ты себя недооцениваешь?"},
    "выбор": {"theme": "Две дороги в лесу", "heroes": "Лиса и Ёж", "conclusion": "Выбор — это принятие последствий", "hook": "Какой выбор ты откладываешь?"},
    "маски": {"theme": "Павлин и воробей", "heroes": "Павлин и Воробей", "conclusion": "Маска скрывает, но не защищает", "hook": "Какую маску ты носишь каждый день?"}
}

def get_pattern_for_theme(theme):
    """Возвращает паттерн для темы"""
    return DEFAULT_PATTERNS.get(theme, DEFAULT_PATTERNS["отношения"])

def create_post_now():
    """Генерирует и публикует один пост"""
    
    print("\n" + "="*70)
    print("СОЗДАНИЕ ПОСТА")
    print("="*70 + "\n")
    
    theme = random.choice(THEMES)
    print(f"1. ТЕМА: {theme}")
    
    print("2. ГЕНЕРИРУЕМ ПАТТЕРН")
    pattern = get_pattern_for_theme(theme)
    print(f"   Герои: {pattern['heroes']}")
    print(f"   Хук: {pattern['hook']}")
    
    print("\n3. ГЕНЕРИРУЕМ КОНТЕНТ")
    post = generate_post_content(pattern)
    print(f"   Caption: {len(post['caption'].split())} слов")
    
    print("\n4. ГЕНЕРИРУЕМ ИЗОБРАЖЕНИЕ")
    output_dir = f"/root/factory/output/post_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(output_dir, exist_ok=True)
    post_image_path = f"{output_dir}/image.jpg"
    
    img, path = generate_flux_image(post['image_description'], post_image_path)
    if img:
        print(f"   OK - Изображение готово")
    else:
        print(f"   ERROR - Не удалось создать изображение")
        return None
    
    print("\n5. ПУБЛИКУЕМ НА VK")
    vk_url = publish_post_to_vk(post['caption'], post_image_path)
    
    if vk_url:
        print("\n" + "="*70)
        print("✅ ПОСТ ОПУБЛИКОВАН!")
        print("="*70)
        print(f"Тема: {theme}")
        print(f"VK: {vk_url}")
        print("="*70 + "\n")
        return vk_url
    else:
        print("ERROR при публикации")
        return None

if __name__ == "__main__":
    create_post_now()
