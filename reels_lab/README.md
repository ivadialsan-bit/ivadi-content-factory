# Reels Lab — программная анимация, русский голос и SFX

Изолированный пилот для Windows. Видео полностью создаётся кодом (Pillow + FFmpeg), без исходных фото и видео, видеогенераторов, платных API и изменения сервисов Content Factory. Предмет ролика: как сделать ответ ИИ конкретнее; в финале концепт набора промптов за 890 ₽. Это **тест оффера**, а не действующая продажа.

## Быстрый запуск (Windows PowerShell)

1. Установить Python 3.11/3.12 и FFmpeg с доступом через PATH.
2. В корне клонированного репозитория:

    python -m venv .venv-reels

    .\.venv-reels\Scripts\python.exe -m pip install -r reels_lab/requirements-base.txt

    .\.venv-reels\Scripts\python.exe -m pip install edge-tts

    .\.venv-reels\Scripts\python.exe -m reels_lab.cli --dry-run

    .\.venv-reels\Scripts\python.exe -m reels_lab.cli --engine edge --preview --output reels_lab/out/preview.mp4

    .\.venv-reels\Scripts\python.exe -m reels_lab.cli --engine edge --output reels_lab/out/reels_890.mp4

Edge использует сетевой сервис Microsoft (без отдельного ключа), поэтому зависит от доступности сервиса и его правил; отсутствие счёта за API не означает безусловную лицензию на коммерческую эксплуатацию. Это **контрольный**, а не гарантированно лучший голос. Итоговый размер 1080×1920, 30 fps; превью 540×960, 15 fps.

## Улучшенная русская озвучка — локальные модели

Модели тяжёлые. Установку каждого движка выполнять в **отдельном виртуальном окружении** — не смешивать Chatterbox и Qwen, чтобы избежать конфликтов версий PyTorch/torchaudio. Заранее запустить:

    powershell -ExecutionPolicy Bypass -File reels_lab/windows_check.ps1

Qwen3-TTS, официальный исходник: https://github.com/QwenLM/Qwen3-TTS. Для 1.7B VoiceDesign, включая русский и управление стилем, установка в новом окружении:

    python -m venv .venv-qwen

    .\.venv-qwen\Scripts\python.exe -m pip install -r reels_lab/requirements-base.txt

    .\.venv-qwen\Scripts\python.exe -m pip install qwen-tts soundfile

    .\.venv-qwen\Scripts\python.exe -m reels_lab.cli --engine qwen --output reels_lab/out/reels_qwen.mp4

Chatterbox Multilingual V3, официальный исходник: https://github.com/resemble-ai/chatterbox. Поддерживает ru; проект объявлен архивным и больше не поддерживается:

    python -m venv .venv-chatterbox

    .\.venv-chatterbox\Scripts\python.exe -m pip install -r reels_lab/requirements-base.txt

    .\.venv-chatterbox\Scripts\python.exe -m pip install chatterbox-tts

    .\.venv-chatterbox\Scripts\python.exe -m reels_lab.cli --engine chatterbox --output reels_lab/out/reels_chatterbox.mp4

Код намеренно требует CUDA по умолчанию для тяжёлых моделей. Опция --device cpu снимает проверку GPU, но может быть непрактична по памяти и времени. Модели могут скачивать несколько гигабайт при первом запуске; не ставить на маленький Timeweb-сервер. Никакие веса, голоса или секреты в GitHub не загружаются. Для клонирования голоса необходимо согласие владельца образца, которое этот пилот не собирает и образцы не использует.

## Если озвучка уже записана

Сложить собственные или полученные с согласия автора файлы WAV в папку voice_inputs: 01.wav, 02.wav, 03.wav, 04.wav. Длительность кадра автоматически подстраивается под длительность каждой фразы:

    python -m reels_lab.cli --engine external --external-dir voice_inputs --output reels_lab/out/reels_own_voice.mp4

## Сравнение качества (не имитировать)

Использовать один story_890.json для всех 3 движков; получить 3 MP4 и прослушать без подсказок, какой моделью озвучено. Оценить произношение слова "ИИ", числительных, пауз, естественность голоса, наличие артефактов, скорость и затраты памяти. Протокол: docs/voice_scorecard.md. Тесты кода **не доказывают**, что одна модель звучит лучше. Без локального GPU или свободной памяти сравнение Qwen и Chatterbox остаётся заблокированным, это честно отражается в отчёте.

## Видео, звуковой дизайн и качество

- Анимированная геометрия, карточки, кинетические заголовки и звуки кликов генерируются математически. Сторонние звуковые наборы не скачиваются, лицензии SFX не требуются.
- Тайминг видеосцен берётся из **реальной длительности** TTS-файлов (48 kHz PCM WAV), а не из заранее угаданного числа секунд.
- Аудио нормализуется FFmpeg, эффект намеренно тише речи.
- Отсутствующий Montserrat не подменяется скрытно: используемый файл шрифта указывается через --font путь; иначе скрипт берёт доступный жирный кириллический шрифт. Не коммитить платные или чужие шрифты.
- После рендера формируется *.report.json с длительностью, движком и флагом voice_tested_by_human=false.
- Перед публикацией человек должен подтвердить читаемость, дикцию, ударения и права на выбранный голос.

## Проверка

    python -m unittest discover -s reels_lab/tests -v

Контроль статуса:
- GitHub: код, инструкции и тесты
- Работоспособность: локальная проверка + (если настроено) CI
- Качество русского голоса: до реального сравнительного прослушивания **не подтверждено**
- Продажи, публикация и доставка продукта: не подключены

## Безопасность

Никаких паролей, токенов, ключей, пользовательских голосовых образцов в репозиторий. Никогда не запускать модели через случайные "халявные" API-прокси. Не менять production-сервис Content Factory. Файлы MP4 и рабочие папки игнорируются через reels_lab/.gitignore.
