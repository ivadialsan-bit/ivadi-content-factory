import json
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SHEET_ID = "1kB4F_zPEJKKJ-EcwKnrR_mS5-gVegyfDsAp7JR23F40"

PUBLICATION_SCHEDULE = {
    "пост": ["09:00", "21:00"],
    "карусель": ["15:00"]
}

def save_to_sheets(post_data, carousel_data, pattern):
    """Сохраняет пост и карусель в Sheets с расписанием"""
    creds = Credentials.from_service_account_file("/root/factory/google_credentials.json", scopes=SCOPES)
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_ID).worksheet("Публикации")
    
    now = datetime.now()
    
    # Пост
    for time_slot in PUBLICATION_SCHEDULE["пост"]:
        pub_time = datetime.strptime(f"{now.date()} {time_slot}", "%Y-%m-%d %H:%M")
        if pub_time < now:
            pub_time += timedelta(days=1)
        
        post_row = [
            f"POST_{now.strftime('%Y%m%d_%H%M%S')}",
            pub_time.strftime('%d.%m.%Y'),
            "club239316119",
            "пост",
            pattern['Хук'],
            f"готов к публикации | {pub_time.strftime('%H:%M')}",
            "",
            "",
            "", "", "", "",
            f"Автопубликация {pub_time.strftime('%H:%M')}",
            json.dumps(post_data, ensure_ascii=False)
        ]
        ws.append_row(post_row)
    
    # Карусель
    for time_slot in PUBLICATION_SCHEDULE["карусель"]:
        pub_time = datetime.strptime(f"{now.date()} {time_slot}", "%Y-%m-%d %H:%M")
        if pub_time < now:
            pub_time += timedelta(days=1)
        
        carousel_row = [
            f"CAROUSEL_{now.strftime('%Y%m%d_%H%M%S')}",
            pub_time.strftime('%d.%m.%Y'),
            "club239316119",
            "карусель",
            pattern['Хук'],
            f"готов к публикации | {pub_time.strftime('%H:%M')}",
            "",
            "",
            "", "", "", "",
            f"Автопубликация {pub_time.strftime('%H:%M')}",
            json.dumps(carousel_data, ensure_ascii=False)
        ]
        ws.append_row(carousel_row)
    
    print("✅ Пост и карусель сохранены в Sheets с расписанием")
    return True

if __name__ == "__main__":
    test_post = {"caption": "Test", "cta": "Test"}
    test_carousel = {"slides": [], "cta": "Test"}
    test_pattern = {"Хук": "Test hook"}
    
    save_to_sheets(test_post, test_carousel, test_pattern)
