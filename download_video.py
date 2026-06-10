import requests, time, jwt
import urllib3
urllib3.disable_warnings()

ACCESS = 'AF8hYKAKbL3rfrCLeJP3Ky9f4feNN4fe'
SECRET = 'MfY3HCdTKNPaPDKHEdaRKhKGQPMhmmCT'

def get_token():
    payload = {'iss': ACCESS, 'exp': int(time.time())+1800, 'nbf': int(time.time())-5}
    return jwt.encode(payload, SECRET, algorithm='HS256')

def create_video(prompt):
    headers = {'Authorization': f'Bearer {get_token()}', 'Content-Type': 'application/json'}
    data = {'model': 'kling-v1', 'prompt': prompt, 'duration': 5, 'aspect_ratio': '9:16'}
    r = requests.post('https://api.klingai.com/v1/videos/text2video', headers=headers, json=data, verify=False)
    return r.json()['data']['task_id']

def wait_and_download(task_id, filename='test_video.mp4'):
    for i in range(60):
        headers = {'Authorization': f'Bearer {get_token()}'}
        r = requests.get(f'https://api.klingai.com/v1/videos/text2video/{task_id}', headers=headers, verify=False)
        data = r.json()
        status = data['data']['task_status']
        print(f'Статус: {status}')
        if status == 'succeed':
            url = data['data']['task_result']['videos'][0]['url']
            video = requests.get(url, verify=False)
            with open(filename, 'wb') as f:
                f.write(video.content)
            print(f'Видео сохранено: {filename}')
            return filename
        time.sleep(10)
    return None

if __name__ == '__main__':
    task_id = create_video('Galaxy formation timelapse, cinematic 4k, deep space')
    print(f'Task: {task_id}')
    wait_and_download(task_id)
