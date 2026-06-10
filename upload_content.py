import os
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import sys
sys.path.insert(0, "/root/factory")
from config import DRIVE_FOLDER_ID, COMMUNITY_ID, CONTENT_TYPE

def upload_carousel_to_drive(carousel_paths, post_data, carousel_data):
    """Загружает карусель на Google Drive"""
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(
        "/root/factory/google_credentials.json", 
        scopes=SCOPES
    )
    drive = build('drive', 'v3', credentials=creds)
    
    today = datetime.now()
    hook_title = post_data['cta'][:40].replace('/', '-').replace('\\', '-')
    
    # Имя папки: паблик/тип_контента/месяц/дата_название
    folder_path = f"{COMMUNITY_ID}/карусель/{today.strftime('%Y-%m')}/{today.strftime('%d')}__{hook_title}"
    
    # Загружаем каждый слайд
    for i, slide_path in enumerate(carousel_paths):
        file_metadata = {
            'name': f"{folder_path}/slide_{i+1}.jpg",
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(slide_path, mimetype='image/jpeg', resumable=True)
        drive.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    print(f"   OK - {len(carousel_paths)} слайдов загружены на Drive")
    return f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"

def upload_post_image_to_drive(post_image_path, post_data):
    """Загружает изображение поста на Google Drive"""
    SCOPES = ['https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(
        "/root/factory/google_credentials.json", 
        scopes=SCOPES
    )
    drive = build('drive', 'v3', credentials=creds)
    
    today = datetime.now()
    hook_title = post_data['cta'][:40].replace('/', '-').replace('\\', '-')
    
    folder_path = f"{COMMUNITY_ID}/пост/{today.strftime('%Y-%m')}/{today.strftime('%d')}__{hook_title}"
    
    file_metadata = {
        'name': f"{folder_path}/image.jpg",
        'parents': [DRIVE_FOLDER_ID]
    }
    media = MediaFileUpload(post_image_path, mimetype='image/jpeg', resumable=True)
    drive.files().create(body=file_metadata, media_body=media, fields='id').execute()
    
    print(f"   OK - Изображение поста загружено на Drive")
    return f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"

