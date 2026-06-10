import requests
import json

# Жёсткие ключи
VK_TOKEN = "vk1.a.C_iFsJv4x2dHla9am-0GDQ069..."
VK_GROUP_ID = "239316119"

def publish_post_to_vk(caption, image_path):
    """Публикует пост с изображением на VK"""
    
    print("      Загружаем изображение...")
    
    # Получаем URL для загрузки фото
    upload_url_response = requests.get(
        "https://api.vk.com/method/photos.getWallUploadServer",
        params={
            "access_token": VK_TOKEN,
            "group_id": VK_GROUP_ID,
            "v": "5.131"
        }
    )
    
    upload_url = upload_url_response.json()["response"]["upload_url"]
    
    # Загружаем фото
    with open(image_path, "rb") as f:
        files = {"photo": f}
        upload_response = requests.post(upload_url, files=files)
    
    upload_data = upload_response.json()
    
    # Сохраняем фото
    save_response = requests.get(
        "https://api.vk.com/method/photos.saveWallPhoto",
        params={
            "access_token": VK_TOKEN,
            "group_id": VK_GROUP_ID,
            "photo": upload_data["photo"],
            "server": upload_data["server"],
            "hash": upload_data["hash"],
            "v": "5.131"
        }
    )
    
    save_json = save_response.json()
    
    if "error" in save_json:
        print(f"      VK Error: {save_json['error']['error_msg']}")
        return None
    
    photo_id = save_json["response"][0]["id"]
    photo_owner = save_json["response"][0]["owner_id"]
    
    print(f"      OK - изображение загружено")
    
    # Публикуем пост
    publish_params = {
        "access_token": VK_TOKEN,
        "owner_id": f"-{VK_GROUP_ID}",
        "message": caption,
        "attachments": f"photo{photo_owner}_{photo_id}",
        "v": "5.131"
    }
    
    publish_response = requests.get(
        "https://api.vk.com/method/wall.post",
        params=publish_params
    )
    
    pub_json = publish_response.json()
    
    if "error" in pub_json:
        print(f"      VK Error: {pub_json['error']['error_msg']}")
        return None
    
    if "response" in pub_json:
        post_id = pub_json["response"]["post_id"]
        vk_url = f"https://vk.com/club{VK_GROUP_ID}?w=wall-{VK_GROUP_ID}_{post_id}"
        return vk_url
    
    return None

def publish_carousel_to_vk(carousel_paths, caption):
    """Публикует карусель на VK"""
    
    attachments = []
    
    for i, slide_path in enumerate(carousel_paths):
        print(f"      Слайд {i+1}...")
        
        upload_url_response = requests.get(
            "https://api.vk.com/method/photos.getWallUploadServer",
            params={
                "access_token": VK_TOKEN,
                "group_id": VK_GROUP_ID,
                "v": "5.131"
            }
        )
        
        upload_url = upload_url_response.json()["response"]["upload_url"]
        
        with open(slide_path, "rb") as f:
            files = {"photo": f}
            upload_response = requests.post(upload_url, files=files)
        
        upload_data = upload_response.json()
        
        save_response = requests.get(
            "https://api.vk.com/method/photos.saveWallPhoto",
            params={
                "access_token": VK_TOKEN,
                "group_id": VK_GROUP_ID,
                "photo": upload_data["photo"],
                "server": upload_data["server"],
                "hash": upload_data["hash"],
                "v": "5.131"
            }
        )
        
        save_json = save_response.json()
        
        if "error" in save_json:
            print(f"      VK Error")
            continue
        
        photo_id = save_json["response"][0]["id"]
        photo_owner = save_json["response"][0]["owner_id"]
        
        attachments.append(f"photo{photo_owner}_{photo_id}")
    
    if not attachments:
        return None
    
    publish_params = {
        "access_token": VK_TOKEN,
        "owner_id": f"-{VK_GROUP_ID}",
        "message": caption,
        "attachments": ",".join(attachments),
        "v": "5.131"
    }
    
    publish_response = requests.get(
        "https://api.vk.com/method/wall.post",
        params=publish_params
    )
    
    pub_json = publish_response.json()
    
    if "response" in pub_json:
        post_id = pub_json["response"]["post_id"]
        vk_url = f"https://vk.com/club{VK_GROUP_ID}?w=wall-{VK_GROUP_ID}_{post_id}"
        return vk_url
    
    return None
