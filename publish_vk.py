import requests

VK_TOKEN = "vk1.a.C_iFsJv4x2dHla9am-0GDQ069-1pNBRqB4aULyCZEZ7nn85QTWmEn3Ebj8NzQKwZE3O3A2kI1yN78MQqlafwobqoHKY20ozjY-Qv-de1K7Y_cqTO0gaJ42smA3nxUsn2n_xpFyI_eqkHiYUVV09gMw5V6vQgTeKXIVbD7easQYliwc1ejXBfLsL4AyWZdO1SsPsK6cQPPq8rTRGlWzdVSg"
VK_GROUP_ID = "239316119"
API_VERSION = "5.131"

def upload_video(file_path, title="AI Clip", description=""):
    r = requests.get("https://api.vk.com/method/video.save", params={
        "access_token": VK_TOKEN,
        "v": API_VERSION,
        "group_id": VK_GROUP_ID,
        "name": title,
        "description": description,
    })
    data = r.json()
    if "error" in data:
        print(f"ERROR video.save: {data['error']}")
        return None
    upload_url = data["response"]["upload_url"]
    video_id = data["response"]["video_id"]
    owner_id = data["response"]["owner_id"]
    print(f"Uploading: {file_path}")
    with open(file_path, "rb") as f:
        r2 = requests.post(upload_url, files={"video_file": f})
    print(f"Upload status: {r2.status_code}")
    print(f"Video URL: https://vk.com/video{owner_id}_{video_id}")
    return f"{owner_id}_{video_id}"

if __name__ == "__main__":
    result = upload_video("/root/factory/final_clip.mp4", title="AI Clip Test")
    print(f"Done: {result}")
