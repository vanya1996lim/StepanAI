import subprocess
import os
import json
import asyncio
import logging
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import tempfile

logger = logging.getLogger(__name__)

# ===== AI НАРІЗКА — знаходить кращі моменти =====

def detect_best_moments(video_path: str, min_duration: int = 30, max_duration: int = 90, max_clips: int = 20) -> list:
    """Ділить відео на рівні кліпи."""
    probe_cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_format', video_path
    ]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    import json as _json
    info = _json.loads(result.stdout)
    total_duration = float(info['format']['duration'])

    logger.info(f"Тривалість відео: {total_duration:.0f} сек")

    clips = []
    current = 0
    while current + min_duration < total_duration:
        clip_end = min(current + max_duration, total_duration)
        clips.append((current, clip_end))
        current = clip_end
        if len(clips) >= max_clips:
            break

    logger.info(f"Знайдено {len(clips)} кліпів")
    return clips


# ===== КОНВЕРТАЦІЯ 16:9 → 9:16 з розмитим фоном =====

def convert_to_vertical(input_path: str, output_path: str, start: float, duration: float):
    """
    Конвертує горизонтальне відео в вертикальний формат 9:16
    з розмитим фоном з того ж відео.
    """
    # Розміри вихідного відео (1080x1920 — Full HD вертикальне)
    out_w, out_h = 1080, 1920

    # Розмір центрального відео (вся ширина)
    vid_w = out_w
    vid_h = int(out_w * 9 / 16)  # ~607px

    # Позиція центрального відео
    vid_y = (out_h - vid_h) // 2

    # FFmpeg команда:
    # 1. Розмитий фон — розтягуємо на весь екран і блюримо
    # 2. Оригінальне відео по центру
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(start),
        '-i', input_path,
        '-t', str(duration),
        '-filter_complex',
        (
            f'[0:v]scale={out_w}:{out_h},boxblur=20:5[bg];'
            f'[0:v]scale={vid_w}:{vid_h}[vid];'
            f'[bg][vid]overlay=0:{vid_y}[out]'
        ),
        '-map', '[out]',
        '-map', '0:a',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'fast',
        '-crf', '23',
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg помилка: {result.stderr}")


# ===== НАКЛАДАННЯ МАСКОТА =====

def add_mascot(video_path: str, output_path: str, mascot_path: str):
    """Накладає маскота PNG на відео внизу праворуч."""

    if not os.path.exists(mascot_path):
        logger.warning("Маскот не знайдено, пропускаємо")
        # Просто копіюємо
        import shutil
        shutil.copy(video_path, output_path)
        return

    # Розміри відео
    out_w, out_h = 1080, 1920
    mascot_h = 480  # висота маскота в пікселях
    
    # Отримуємо розміри маскота щоб зберегти пропорції
    img = Image.open(mascot_path)
    ratio = mascot_h / img.height
    mascot_w = int(img.width * ratio)

    # Позиція — внизу праворуч впритул до краю
    mascot_x = out_w - mascot_w - 20
    mascot_y = out_h - mascot_h

    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-i', mascot_path,
        '-filter_complex',
        (
            f'[1:v]scale={mascot_w}:{mascot_h}[mascot];'
            f'[0:v][mascot]overlay={mascot_x}:{mascot_y}'
        ),
        '-map', '0:a',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'fast',
        '-crf', '23',
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg overlay помилка: {result.stderr}")


# ===== ДОДАВАННЯ ТЕКСТУ =====

def add_title_text(video_path: str, output_path: str, title: str):
    """Додає білий жирний текст з чорною обводкою зверху відео."""

    out_w, out_h = 1080, 1920
    font_size = 70
    # Позиція тексту — по центру у верхній зоні
    text_y = 120

    # Екрануємо спецсимволи для FFmpeg
    safe_title = title.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")

    cmd = [
        'ffmpeg', '-y',
        '-i', video_path,
        '-vf', (
            f"drawtext=text='{safe_title}'"
            f":fontsize={font_size}"
            f":fontcolor=white"
            f":borderw=4"
            f":bordercolor=black"
            f":x=(w-text_w)/2"
            f":y={text_y}"
            f":fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            f":line_spacing=10"
        ),
        '-map', '0:a',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-preset', 'fast',
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Якщо шрифт не знайдено — без тексту
        logger.warning(f"Не вдалось додати текст: {result.stderr[:200]}")
        import shutil
        shutil.copy(video_path, output_path)


# ===== ГЕНЕРАЦІЯ ЗАГОЛОВКУ через OpenAI =====

async def generate_title(video_path: str, original_title: str = "") -> str:
    """Генерує заголовок для кліпу через OpenAI."""
    try:
        import openai
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return original_title or "Дивись до кінця!"

        client = openai.AsyncOpenAI(api_key=api_key)
        prompt = (
            f"Придумай короткий яскравий заголовок українською мовою для відео-рілсу. "
            f"Назва оригінального відео: '{original_title}'. "
            f"Заголовок має бути до 8 слів, без емодзі, великими літерами, "
            f"інтригуючий щоб хотілось дивитись. Відповідай тільки заголовком."
        )

        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )
        title = response.choices[0].message.content.strip()
        return title.upper()
    except Exception as e:
        logger.warning(f"OpenAI помилка: {e}")
        return original_title or "ДИВИСЬ ДО КІНЦЯ"


# ===== ГОЛОВНА ФУНКЦІЯ ОБРОБКИ =====

async def process_video(video_path: str, mascot_path: str = "data/mascot.png") -> list:
    """
    Повний цикл обробки відео:
    1. Знаходить кращі моменти
    2. Конвертує в 9:16 з розмитим фоном
    3. Накладає маскота
    4. Додає заголовок
    Повертає список шляхів до готових кліпів.
    """
    os.makedirs("temp/clips", exist_ok=True)

    # Знаходимо кращі моменти
    loop = asyncio.get_event_loop()
    moments = await loop.run_in_executor(None, detect_best_moments, video_path)

    if not moments:
        raise ValueError("Не знайдено підходящих моментів у відео")

    ready_clips = []

    for i, (start, end) in enumerate(moments):
        duration = end - start
        clip_id = f"clip_{i+1:02d}"

        try:
            # Крок 1 — вертикальний формат з розмитим фоном
            vertical_path = f"temp/clips/{clip_id}_vertical.mp4"
            await loop.run_in_executor(
                None, convert_to_vertical, video_path, vertical_path, start, duration
            )

            # Крок 2 — накладаємо маскота
            mascot_path_out = f"temp/clips/{clip_id}_mascot.mp4"
            await loop.run_in_executor(
                None, add_mascot, vertical_path, mascot_path_out, mascot_path
            )

            # Крок 3 — генеруємо заголовок
            video_name = os.path.basename(video_path).replace('.mp4', '')
            title = await generate_title(mascot_path_out, video_name)

            # Крок 4 — додаємо текст
            final_path = f"temp/clips/{clip_id}_final.mp4"
            await loop.run_in_executor(
                None, add_title_text, mascot_path_out, final_path, title
            )

            ready_clips.append({
                'path': final_path,
                'title': title,
                'duration': duration,
                'start': start
            })

            # Видаляємо тимчасові файли
            for tmp in [vertical_path, mascot_path_out]:
                if os.path.exists(tmp):
                    os.remove(tmp)

            logger.info(f"✅ Кліп {i+1}/{len(moments)} готовий: {title}")

        except Exception as e:
            logger.error(f"❌ Помилка кліпу {i+1}: {e}")
            continue

    logger.info(f"Готово {len(ready_clips)} кліпів з {len(moments)}")
    return ready_clips
