import subprocess
import os
import asyncio
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def detect_best_moments(video_path, min_duration=30, max_duration=90, max_clips=20):
    probe_cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', video_path]
    result = subprocess.run(probe_cmd, capture_output=True, text=True)
    import json
    total_duration = float(json.loads(result.stdout)['format']['duration'])
    logger.info(f"Тривалість: {total_duration:.0f} сек")
    clips = []
    current = 0
    while current + min_duration < total_duration and len(clips) < max_clips:
        clip_end = min(current + max_duration, total_duration)
        clips.append((current, clip_end))
        current = clip_end
    logger.info(f"Кліпів: {len(clips)}")
    return clips

def convert_to_vertical(input_path, output_path, start, duration):
    cmd = ['ffmpeg', '-y', '-ss', str(start), '-i', input_path, '-t', str(duration),
           '-filter_complex',
           '[0:v]scale=1080:1920,boxblur=20:5[bg];[0:v]scale=1080:607[vid];[bg][vid]overlay=0:656[out]',
           '-map', '[out]', '-map', '0:a', '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'fast', output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg: {r.stderr[-500:]}")

def add_mascot(video_path, output_path, mascot_path):
    if not os.path.exists(mascot_path):
        import shutil
        shutil.copy(video_path, output_path)
        return
    img = Image.open(mascot_path)
    mascot_h = 480
    mascot_w = int(img.width * mascot_h / img.height)
    x = 1080 - mascot_w - 20
    y = 1920 - mascot_h
    cmd = ['ffmpeg', '-y', '-i', video_path, '-i', mascot_path,
           '-filter_complex', f'[1:v]scale={mascot_w}:{mascot_h}[m];[0:v][m]overlay={x}:{y}',
           '-map', '0:a', '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'fast', output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Mascot: {r.stderr[-300:]}")

async def generate_title(original_title=""):
    try:
        import openai, os
        client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        r = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Придумай короткий яскравий заголовок українською до відео '{original_title}'. До 8 слів, великими літерами, без емодзі."}],
            max_tokens=50)
        return r.choices[0].message.content.strip().upper()
    except:
        return original_title.upper() if original_title else "ДИВИСЬ ДО КІНЦЯ"

def add_title(video_path, output_path, title):
    safe = title.replace("'", "").replace(":", "").replace("\\", "")[:50]
    cmd = ['ffmpeg', '-y', '-i', video_path,
           '-vf', f"drawtext=text='{safe}':fontsize=65:fontcolor=white:borderw=4:bordercolor=black:x=(w-text_w)/2:y=120:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           '-map', '0:a', '-c:v', 'libx264', '-c:a', 'aac', '-preset', 'fast', output_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        import shutil
        shutil.copy(video_path, output_path)

async def process_video(video_path, mascot_path="data/mascot.png"):
    os.makedirs("temp/clips", exist_ok=True)
    loop = asyncio.get_event_loop()
    moments = await loop.run_in_executor(None, detect_best_moments, video_path)
    if not moments:
        raise ValueError("Не знайдено моментів у відео")
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
            ready_clips.append({'path': f, 'title': title, 'duration': end-start})
            for tmp in [v, m]:
                if os.path.exists(tmp): os.remove(tmp)
            logger.info(f"✅ Кліп {i+1}/{len(moments)} готовий")
        except Exception as e:
            logger.error(f"❌ Кліп {i+1}: {e}")
    logger.info(f"Готово {len(ready_clips)} кліпів")
    return ready_clips
