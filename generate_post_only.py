import json
import anthropic

CLAUDE_KEY = "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"

def generate_post_content(pattern):
    """Генерирует caption + optimized image_description для Flux"""
    
    claude = anthropic.Anthropic(
        api_key=CLAUDE_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    
    # Caption
    caption_prompt = f"""Напиши психологический пост (300-500 слов).

Тема: {pattern.get('theme', '')}
Герои: {pattern.get('heroes', '')}
Вывод: {pattern.get('conclusion', '')}
Хук: {pattern.get('hook', '')}

Структура: Крючок → История → Вывод → Вопрос к аудитории
Язык: эмоциональный, разговорный, психологичный

Ответ ТОЛЬКО текст."""

    msg1 = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        messages=[{"role": "user", "content": caption_prompt}]
    )
    
    caption = msg1.content[0].text.strip()
    
    # Image Description - ОПТИМИЗИРОВАННЫЙ для Flux
    image_prompt = f"""На основе текста создай КРАТКИЙ промпт для Flux (40-60 слов).

ТЕКСТ:
{caption}

Формат промпта:
"Cinematic dramatic [style]: [main scene with both animals]. [emotional contrast]. [lighting]. [quality words]"

Примеры слов:
- Стили: oil painting, photorealistic, dark fantasy
- Животные: ant, grasshopper, wolf, fox, cat, dog (используй из текста)
- Эмоции: tension, joy, despair, hope, freedom
- Свет: dramatic lighting, moody, golden hour, shadows
- Качество: masterpiece, 8k quality, detailed, professional

Ответ ТОЛЬКО промпт (одна строка, 40-60 слов), БЕЗ JSON, БЕЗ комментариев."""

    msg2 = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": image_prompt}]
    )
    
    image_description = msg2.content[0].text.strip()
    
    # CTA
    cta_prompt = f"""Создай финальный вопрос (макс 10 слов) с эмодзи для этого поста.

ПОСТ:
{caption}

Ответ ТОЛЬКО вопрос."""

    msg3 = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[{"role": "user", "content": cta_prompt}]
    )
    
    cta = msg3.content[0].text.strip()
    
    return {
        "caption": caption,
        "image_description": image_description,
        "cta": cta
    }
