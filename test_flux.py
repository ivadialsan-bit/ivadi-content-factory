import sys
sys.path.insert(0, "/root/factory")
from config import FAL_API_KEY
import requests
resp = requests.post("https://flux-proxy.ivadialsan.workers.dev/",headers={"x-api-key":FAL_API_KEY},json={"prompt":"Egypt beach autumn sunset cinematic","num_inference_steps":20,"image_size":"landscape_16_9"},timeout=60)
print("STATUS:",resp.status_code)
data=resp.json()
print("OK:",data["images"][0]["url"][:80]) if "images" in data else print("ERR:",data)
