import subprocess
import os

def merge_video_audio(video_path, audio_path, output_path):
    cmd = [
        'ffmpeg', '-i', video_path, '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-shortest',
        '-y', output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f'Готово: {output_path}')
        return output_path
    else:
        print(f'Ошибка: {result.stderr}')
        return None

if __name__ == '__main__':
    merge_video_audio(
        '/root/factory/test_video.mp4',
        '/root/factory/test_audio.mp3',
        '/root/factory/final_clip.mp4'
    )
