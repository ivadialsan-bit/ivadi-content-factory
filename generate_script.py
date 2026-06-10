import gspread
import anthropic
import json
import re
import sys
sys.path.insert(0, "/root/factory")
from config import CLAUDE_API_KEY
from google.oauth2.service_account import Credentials

SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_ID = "1kB4F_zPEJKKJ-EcwKnrR_mS5-gVegyfDsAp7JR23F40"

def get_next_pattern():
    creds = Credentials.from_service_account_file("/root/factory/google_credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).worksheet("Паттерны")
    rows = ws.get_all_records()
    for i, row in enumerate(rows):
        if row["Статус"] == "очередь":
            ws.update_cell(i + 2, 7, "в работе")
            return row, i + 2
    return None, None

def generate_script(pattern):
    claude = anthropic.Anthropic(
        api_key=CLAUDE_API_KEY,
        base_url="https://anthropic-proxy.ivadialsan.workers.dev",
    )
    prompt = f"""Ты пишешь ПСИХОЛОГИЧЕСКИЕ ПРИТЧИ про животных. Не просто рассказ, а ГЛУБОКАЯ ИСТОРИЯ о человеческих поступках, выборе, ошибках. Животные — метафора для универсальных ситуаций, в которых узнает себя МАКСИМУМ людей.

ГЛАВНОЕ: История должна ЗАХВАТЫВАТЬ и УДЕРЖИВАТЬ внимание. Каждое слово важно.

ПРИМЕРЫ ТЕМУ (выбери близко к теме паттерна):
- Одиночество в толпе
- Страх перед неизвестным  
- Зависть и сравнение
- Предательство близких
- Выбор между легким и правильным
- Ложное чувство безопасности
- Иллюзия контроля
- Привычка вредит больше чем помогает
- Молчание может убить
- Давление общества vs собственное мнение Каждая история раскрывает универсальную человеческую тему через цепочку событий.

ОБРАЗЕЦ СТРУКТУРЫ И МЕХАНИКИ:
"После долгого дня вспашки земли бык вернулся в хлев и лег отдохнуть. Рядом сидел кот, и бык ему сказал: «Сегодня я очень устал. Завтра хочу только отдыхать». Кот пошел и сказал собаке: «Хозяин слишком давит на быка. Он так измотан, что больше не хочет работать». Чуть позже собака увидела овцу и сказала ей: «Бык, возможно, завтра бросит работу, потому что очень устал». Овца передала свинье: «Бык с завтрашнего дня больше не будет работать, потому что его работа тяжела, а хозяин еще и бьет его кнутом». Вечером того же дня, когда слуга хозяина кормил свинью, та сказала ему: «Бык собирается завтра бросить работу и уйти. Другие хозяева намного лучше. Они не бьют кнутом и не морят своих животных голодом». Слуга тут же сообщил хозяину, что бык собирается поднять бунт и уйти вместе с другими животными. Услышав это, хозяин решил немедленно избавиться от быка, чтобы он не создавал проблем. Быка лишили жизни."

ЧТО РАБОТАЕТ В ОБРАЗЦЕ:
- Цепочка персонажей (кот → собака → овца → свинья → слуга)
- Каждый добавляет деталь от себя, искажая оригинал
- Напряжение нарастает к финалу
- Прямая речь в кавычках — живо и конкретно
- Финал неожиданный но логичный
- Мораль переключает с животных на читателя

ТВОЯ ЗАДАЧА:
Напиши историю ПО ЭТОЙ МЕХАНИКЕ но с ДРУГИМ СЮЖЕТОМ.

ТЕМА: {pattern["Тема"]}
ГЕРОИ: {pattern["Герои"]}
ВЫВОД: {pattern["Вывод"]}
ХУК: {pattern["Хук"]}
CTA ТРИГГЕР: {pattern["CTA триггер"]}

ТРЕБОВАНИЯ:
- Длина: 100-120 слов (40 секунд озвучки)
- Структура: Завязка (1-2 сцены) → Цепочка персонажей (3-4 звена) → Финал (неожиданный)
- Язык: Прямая речь в кавычках, разговорный русский, без литературности
- Мораль: 1-2 фразы в конце, которая бьёт в личный опыт
- Не повторять историю про быка и молчание

ПРАВИЛА ОЗВУЧКИ (SSML разметка):
- Вопросы и восклицания: <prosody pitch="+15%">текст</prosody>
- Пауза между репликами: <break time="300ms"/>
- Важные слова (ударение): <emphasis level="strong">СЛОВО</emphasis>
- Грустные моменты: <prosody rate="0.85">текст</prosody>
- Напряжённые моменты: <prosody pitch="+10%">текст</prosody>

Раздели на 5 сцен для визуала (AI картинки) с указанием ЭФФЕКТА:
- Сцена 1: Завязка (герой в ситуации) — эффект: calm/neutral
- Сцена 2: Первое звено цепочки — эффект: tension
- Сцена 3: Середина (напряжение растёт) — эффект: shock
- Сцена 4: Кульминация (финал приближается) — эффект: revelation
- Сцена 5: Финал и мораль — эффект: calm/sad (зависит от морали)

ЭФФЕКТЫ ДОСТУПНЫ:
- calm: спокойное 1.05x zoom, мягкие цвета
- tension: напряженное 1.15x zoom, насыщенность +30%
- shock: резкое 1.25x zoom, мрачные цвета
- revelation: осознание 1.1x zoom, яркость +10%
- sad: грустное 1.0x zoom, холодные тона

Ответ ТОЛЬКО в JSON без markdown:
{{"hook": "провокационный хук", "script": "полный сценарий 100-120 слов с SSML разметкой", "moral": "мораль 1-2 фразы", "cta": "призыв с триггером", "scenes": ["сцена 1 описание для AI — эффект: calm", "сцена 2 — эффект: tension", "сцена 3 — эффект: shock", "сцена 4 — эффект: revelation", "сцена 5 — эффект: sad/calm"], "effects": ["calm", "tension", "shock", "revelation", "sad"]}}"""

    msg = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)

def save_script(pattern_row, script_data):
    creds = Credentials.from_service_account_file("/root/factory/google_credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).worksheet("Паттерны")
    ws.update_cell(pattern_row, 7, "сценарий готов")
    wq = client.open_by_key(SHEET_ID).worksheet("Очередь")
    next_row = len(wq.get_all_records()) + 2
    wq.update(f"A{next_row}:F{next_row}", [[
        next_row - 1,
        pattern_row - 1,
        "",
        "",
        "ожидает публикации",
        json.dumps(script_data, ensure_ascii=False)
    ]])
    print(f"Сценарий сохранён в очередь")

if __name__ == "__main__":
    print("Берём паттерн из таблицы...")
    pattern, row = get_next_pattern()
    if not pattern:
        print("Нет паттернов в очереди")
        exit()
    print(f"Паттерн: {pattern['Тема']}")
    print("Генерируем сценарий через Claude...")
    script = generate_script(pattern)
    print(f"ХУК: {script['hook']}")
    print(f"МОРАЛЬ: {script['moral']}")
    print(f"СЛОВ В СЦЕНАРИИ: {len(script['script'].split())}")
    print(f"СЦЕНЫ: {len(script['scenes'])} шт")
    save_script(row, script)
    print("ГОТОВО")
