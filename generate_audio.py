import torch
import os

def generate_audio(text, filename="/root/factory/test_audio.mp3"):
    device = torch.device('cpu')
    model, _ = torch.hub.load(
        repo_or_dir='snakers4/silero-models',
        model='silero_tts',
        language='ru',
        speaker='v3_1_ru'
    )
    model.to(device)
    audio = model.apply_tts(
        text=text,
        speaker='aidar',
        sample_rate=48000
    )
    import torchaudio
    torchaudio.save(filename.replace('.mp3', '.wav'), audio.unsqueeze(0), 48000)
    os.system(f"ffmpeg -i {filename.replace('.mp3', '.wav')} {filename} -y")
    print(f"Аудио сохранено: {filename}")
    return filename

if __name__ == "__main__":
    text = "Чёрная дыра разрывает звезду на части. Гравитация настолько мощная, что даже свет не может вырваться наружу."
    generate_audio(text)
