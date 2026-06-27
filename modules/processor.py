import subprocess
import os
import asyncio
import logging
import json
from PIL import Image

logger = logging.getLogger(__name__)

def get_video_info(video_path):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", video_path], capture_output=True, text=True)
    data = json.loads(r.stdout)
    duration = float(data["format"]["duration"])
    width, height = 1920, 1080
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            width = s.get("width", 1920)
            height = s.get("height", 1080)
            break
    return duration, width, height

def detect_best_moments(video_path, min_duration=5, max_duration=90, max_clips=20):
    total, w, h = get_video_info(video_path)
    logger.info(f"Тривалість: {total:.0f} сек, розмір: {w}x{h}")
    if total < min_duration:
        return [(0, total)]
    clips = []
    current = 0
    while current + min_duration < total and len(clips) < max_clips:
        clip_end = min(current + max_duration, total)
        clips.append((current, clip_end))
        current = clip_end
    logger.info(f"Кліпів: {len(clips)}")
    return clips

def convert_to_vertical(input_path, output_path, start, duration):
    # Перевіряємо орієнтацію
    _, w, h = get_video_info(input_path)
    is_vertical = h > w

    if is_vertical:
        cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", input_path, "-t", str(duration), "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2", "-c:v", "libx264", "-c:a", "aac", "-preset", "fast", "-pix_fmt", "yuv420p", output_path]
    else:
        # Горизонтальне — конвертуємо з розмитим фоном
        cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", input_path, "-t", str(duration),
               "-filter_complex", "[0:v]scale=1080:1920,boxblur=20:5[bg];[0:v]scale=1080:607[vid];[bg][vid]overlay=0:656[out]",
               "-map", "[out]", "-map", "0:a", "-c:v", "libx264", "-c:a", "aac", "-preset", "fast", output_path]

    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg: {r.stderr[-300:]}")

def add_mascot(video_path, output_path, mascot_path):
    if not os.path.exists(mascot_path):
        import shutil
        shutil.copy(video_path, output_path)
        return
    img = Image.open(mascot_path)
    h = 480
    w = int(img.width * h / img.height)
    x = 1080 - w - 20
    y = 1920 - h
    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", mascot_path,
           "-filter_complex", f"[1:v]scale={w}:{h}[m];[0:v][m]overlay={x}:{y}",
           "-map", "0:a", "-c:v", "libx264", "-c:a", "aac", "-preset", "fast", output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Mascot: {r.stderr[-200:]}")

async def generate_title(name=""):
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        r = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Придумай короткий заголовок українською до відео {name}. До 8 слів, великими літерами, без емодзі."}],
            max_tokens=50)
        return r.choices[0].message.content.strip().upper()
    except:
        return name.upper()[:50] if name else "ДИВИСЬ ДО КІНЦЯ"

def add_title(video_path, output_path, title):
    safe = title.replace("'", "").replace(":", "").replace("\\", "")[:50]
    cmd = ["ffmpeg", "-y", "-i", video_path,
           "-vf", f"drawtext=text='{safe}':fontsize=65:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=120:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "-map", "0:a", "-c:v", "libx264", "-c:a", "aac", "-preset", "fast", output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        import shutil
        shutil.copy(video_path, output_path)

async def process_video(video_path, mascot_path="data/mascot.png"):
    os.makedirs("temp/clips", exist_ok=True)
    loop = asyncio.get_event_loop()
    moments = await loop.run_in_executor(None, detect_best_moments, video_path)
    ready_clips = []
    for i, (start, end) in enumerate(moments):
        try:
            v = f"temp/clips/clip_{i+1:02d}_v.mp4"
            m = f"temp/clips/clip_{i+1:02d}_m.mp4"
            f = f"temp/clips/clip_{i+1:02d}_final.mp4"
            await loop.run_in_executor(None, convert_to_vertical, video_path, v, start, end-start)
            await loop.run_in_executor(None, add_mascot, v, m, mascot_path)
            title = await generate_title(os.path.basename(video_path))
            await loop.run_in_executor(None, add_title, m, f, title)
            ready_clips.append({"path": f, "title": title, "duration": end-start})
            for tmp in [v, m]:
                if os.path.exists(tmp):
                    os.remove(tmp)
            logger.info(f"Кліп {i+1}/{len(moments)} готовий")
        except Exception as e:
            logger.error(f"Кліп {i+1} помилка: {e}")
    logger.info(f"Готово {len(ready_clips)} кліпів")
    return ready_clips
