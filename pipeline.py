import gspread
import json
import os
import sys
import requests
import time
import subprocess
sys.path.insert(0, "/root/factory")
from effects import EFFECTS, get_effects_for_scene, generate_effects_filter
import re

sys.path.insert(0, "/root/factory")
from config import CLAUDE_API_KEY, KLING_ACCESS, KLING_SECRET, VK_TOKEN, VK_GROUP_ID
from google.oauth2.service_account import Credentials
from generate_image import generate_images_parallel

SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_ID = "1kB4F_zPEJKKJ-EcwKnrR_mS5-gVegyfDsAp7JR23F40"
OUTPUT_DIR = "/root/factory/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_next_script():
    creds = Credentials.from_service_account_file("/root/factory/google_credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).worksheet("Очередь")
    rows = ws.get_all_records()
    for i, row in enumerate(rows):
        if row["Статус"] == "ожидает публикации":
            ws.update_cell(i + 2, 5, "в работе")
            script_data = json.loads(row["Ссылка"])
            return script_data, i + 2
    return None, None

def generate_audio(script_text, output_path):
    from config import ELEVENLABS_API_KEY
    import requests
    
    proxy_url = "https://elevenlabs-proxy.ivadialsan.workers.dev"
    voice_id = "JBFqnCBsd6RMkjVDRZzb"
    
    # Оборачиваем в <speak> для SSML
    ssml_text = f"<speak>{script_text}</speak>"
    
    response = requests.post(
        f"{proxy_url}/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        json={
            "text": ssml_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        },
        timeout=30
    )
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        raise Exception(f"ElevenLabs error: {response.status_code}")
    
    with open(output_path, "wb") as f:
        f.write(response.content)
    return output_path

def generate_subtitles(script_text, audio_duration, output_path):
    sentences = [s.strip() for s in re.split(r"[.!?]+", script_text) if s.strip()]
    duration_per = audio_duration / len(sentences)
    srt = ""
    for i, sent in enumerate(sentences):
        start = i * duration_per
        end = (i + 1) * duration_per
        start_time = f"00:00:{int(start):02d},{int((start % 1) * 1000):03d}"
        end_time = f"00:00:{int(end):02d},{int((end % 1) * 1000):03d}"
        srt += f"{i+1}\n{start_time} --> {end_time}\n{sent}\n\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt)
    return output_path

def merge_video(image_paths, audio_path, subtitle_path, output_path, script_data=None):
    concat_list = f"{OUTPUT_DIR}/concat.txt"
    duration_per_image = 8
    with open(concat_list, "w") as f:
        for img in image_paths:
            f.write(f"file '{img}'\nduration {duration_per_image}\n")
        f.write(f"file '{image_paths[-1]}'\n")
    
    cmd1 = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-vf", "scale=1080:1920", f"{OUTPUT_DIR}/video_temp.mp4"]
    subprocess.run(cmd1, check=True, capture_output=True)
    
    cmd2 = ["ffmpeg", "-y", "-i", f"{OUTPUT_DIR}/video_temp.mp4", "-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-shortest", output_path]
    subprocess.run(cmd2, check=True, capture_output=True)
    
    return output_path

def publish_vk(video_path, title, description):
    r = requests.get("https://api.vk.com/method/video.save", params={
        "access_token": VK_TOKEN,
        "v": "5.131",
        "group_id": VK_GROUP_ID,
        "name": title,
        "description": description,
    })
    data = r.json()
    if "error" in data:
        print(f"VK Error: {data['error']}")
        return None
    upload_url = data["response"]["upload_url"]
    video_id = data["response"]["video_id"]
    owner_id = data["response"]["owner_id"]
    with open(video_path, "rb") as f:
        requests.post(upload_url, files={"video_file": f})
    return f"https://vk.com/video{owner_id}_{video_id}"


def upload_to_drive(video_path, script_data, vk_url):
    """Загружает видео в Google Drive с структурированием"""
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from datetime import datetime
    
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(
        "/root/factory/google_credentials.json", 
        scopes=SCOPES
    )
    drive = build('drive', 'v3', credentials=creds)
    
    # Структура: /VK Клипы/2026-06/№1_Hook_Title/video.mp4
    today = datetime.now()
    month_folder_name = f"{today.strftime('%Y-%m')}"
    
    # Находим или создаём папку "VK Клипы"
    results = drive.files().list(
        q="name='VK Клипы' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields='files(id, name)',
        pageSize=1
    ).execute()
    
    if results['files']:
        root_folder_id = results['files'][0]['id']
    else:
        file_metadata = {
            'name': 'VK Клипы',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        root_folder = drive.files().create(body=file_metadata, fields='id').execute()
        root_folder_id = root_folder.get('id')
        print(f"   📁 Создана папка 'VK Клипы'")
    
    # Находим или создаём папку месяца
    results = drive.files().list(
        q=f"name='{month_folder_name}' and mimeType='application/vnd.google-apps.folder' and parents='{root_folder_id}' and trashed=false",
        spaces='drive',
        fields='files(id, name)',
        pageSize=1
    ).execute()
    
    if results['files']:
        month_folder_id = results['files'][0]['id']
    else:
        file_metadata = {
            'name': month_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [root_folder_id]
        }
        month_folder = drive.files().create(body=file_metadata, fields='id').execute()
        month_folder_id = month_folder.get('id')
        print(f"   📁 Создана папка '{month_folder_name}'")
    
    # Создаём папку для этого видео
    hook_title = script_data['hook'][:30].replace('/', '-')
    video_folder_name = f"{today.strftime('%d')}_{hook_title}"
    
    file_metadata = {
        'name': video_folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [month_folder_id]
    }
    video_folder = drive.files().create(body=file_metadata, fields='id').execute()
    video_folder_id = video_folder.get('id')
    print(f"   📁 Создана папка '{video_folder_name}'")
    
    # Загружаем видео
    file_metadata = {
        'name': f"video.mp4",
        'parents': [video_folder_id]
    }
    media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
    file = drive.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    print(f"   ✅ Видео загружено в Drive")
    
    # Создаём info.txt с метаданными
    info_text = f"""🎬 ИНФОРМАЦИЯ О ВИДЕО
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Дата: {today.strftime('%d.%m.%Y %H:%M')}

📌 ХУК:
{script_data['hook']}

📖 СЦЕНАРИЙ:
{script_data['script']}

💡 МОРАЛЬ:
{script_data['moral']}

🎯 CTA:
{script_data['cta']}

🔗 VK ССЫЛКА:
{vk_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    
    file_metadata = {
        'name': 'info.txt',
        'parents': [video_folder_id]
    }
    drive.files().create(
        body=file_metadata,
        media_body=MediaFileUpload(
            '/tmp/video_info.txt',
            mimetype='text/plain'
        ),
        fields='id'
    ).execute()
    
    with open('/tmp/video_info.txt', 'w', encoding='utf-8') as f:
        f.write(info_text)
    
    file_metadata['name'] = 'info.txt'
    drive.files().create(
        body=file_metadata,
        media_body=MediaFileUpload('/tmp/video_info.txt', mimetype='text/plain'),
        fields='id'
    ).execute()
    
    print(f"   📄 info.txt загружен")
    
    drive_url = f"https://drive.google.com/drive/folders/{video_folder_id}"
    return drive_url


if __name__ == "__main__":
    print("=== СТАРТ ПАЙПЛАЙНА ===")
    print("1. Берём сценарий из очереди...")
    script_data, queue_row = get_next_script()
    if not script_data:
        print("Нет сценариев в очереди, генерируем...")
        subprocess.run(["python3", "/root/factory/generate_script.py"], check=True)
        script_data, queue_row = get_next_script()
        if not script_data:
            print("Не удалось сгенерировать сценарий")
            exit()
    job_id = int(time.time())
    job_dir = f"{OUTPUT_DIR}/{job_id}"
    os.makedirs(job_dir, exist_ok=True)
    print(f"2. Генерируем {len(script_data['scenes'])} картинок...")
    image_paths = generate_images_parallel(script_data["scenes"], job_dir)
    print(f"   Все сцены готовы")
    print("3. Генерируем аудио...")
    audio_path = f"{job_dir}/audio.mp3"
    generate_audio(script_data["script"], audio_path)
    print("   Аудио: OK")
    print("4. Создаём субтитры...")
    subtitle_path = f"{job_dir}/subtitles.srt"
    generate_subtitles(script_data["script"], 40, subtitle_path)
    print("   Субтитры: OK")
    print("5. Склеиваем видео...")
    video_path = f"{job_dir}/final.mp4"
    merge_video(image_paths, audio_path, subtitle_path, video_path, script_data)
    print("   Видео: OK")
    print("6. Публикуем в VK...")
    url = publish_vk(video_path, script_data["hook"], script_data["moral"])
    print(f"   Опубликовано: {url}")
    print("7. Обновляем статус в Sheets...")
    creds = Credentials.from_service_account_file("/root/factory/google_credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).worksheet("Очередь")
    ws.update_cell(queue_row, 5, "опубликовано")
    print("   Статус обновлён")
    print("=== ПАЙПЛАЙН ЗАВЕРШЁН ===")
