import subprocess
import os
import asyncio
import logging
import json
import tempfile
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

def extract_audio(video_path, audio_path):
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", audio_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Audio extract error: {r.stderr[-300:]}")

async def transcribe_audio(audio_path):
    import openai
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with open(audio_path, "rb") as f:
        result = await client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="verbose_json",
            timestamp_granularities=["segment"]
        )
    segments = []
    for seg in result.segments:
        segments.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text
        })
    return segments

async def find_best_moments(segments, total_duration, num_clips=6):
    import openai
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    transcript = "\n".join([f"[{s['start']:.1f}s - {s['end']:.1f}s]: {s['text']}" for s in segments])
    
    prompt = f"""Ти редактор відео для соціальних мереж. Ось транскрипція відео тривалістю {total_duration:.0f} секунд:

{transcript}

Вибери {num_clips} найцікавіших, найсмішніших або найбільш емоційних моментів для рілсів/шортсів.
Кожен момент має бути 30-90 секунд.

Відповідай ТІЛЬКИ у форматі JSON масиву:
[
  {{"start": 12.5, "end": 55.0, "reason": "чому цей момент цікавий"}},
  ...
]"""

    r = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
    )
    
    text = r.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    moments = json.loads(text)
    return [(m["start"], m["end"]) for m in moments]

def convert_to_vertical(input_path, output_path, start, duration):
    _, w, h = get_video_info(input_path)
    is_vertical = h > w
    if is_vertical:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-i", input_path, "-t", str(duration),
            "-filter_complex", "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[out]",
            "-map", "[out]", "-map", "0:a",
            "-c:v", "libx264", "-b:v", "800k", "-c:a", "aac", "-b:a", "128k",
            "-preset", "fast", "-pix_fmt", "yuv420p", output_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-i", input_path, "-t", str(duration),
            "-filter_complex", "[0:v]scale=1080:1920,boxblur=20:5[bg];[0:v]scale=1080:607[vid];[bg][vid]overlay=0:656[out]",
            "-map", "[out]", "-map", "0:a",
            "-c:v", "libx264", "-b:v", "800k", "-c:a", "aac", "-b:a", "128k",
            "-preset", "fast", "-pix_fmt", "yuv420p", output_path
        ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg convert: {r.stderr[-500:]}")

def add_mascot(video_path, output_path, mascot_path):
    if not os.path.exists(mascot_path):
        import shutil
        shutil.copy(video_path, output_path)
        return
    img = Image.open(mascot_path)
    h = 400
    w = int(img.width * h / img.height)
    x = 1080 - w - 20
    y = 1920 - h - 20
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path, "-i", mascot_path,
        "-filter_complex", f"[1:v]scale={w}:{h}[m];[0:v][m]overlay={x}:{y}[out]",
        "-map", "[out]", "-map", "0:a",
        "-c:v", "libx264", "-b:v", "800k", "-c:a", "aac", "-b:a", "128k",
        "-preset", "fast", "-pix_fmt", "yuv420p", output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg mascot: {r.stderr[-500:]}")

async def generate_title(text=""):
    try:
        import openai
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Придумай чіпляючий заголовок українською до цього моменту: {text}. МАКСИМУМ 4 СЛОВА, великими літерами, без емодзі, без розділових знаків."}],
            max_tokens=30)
        return r.choices[0].message.content.strip().upper()
    except:
        return "ДИВИСЬ ДО КІНЦЯ"

def add_title(video_path, output_path, title):
    words = title.replace("'", "").replace(":", "").replace("\\", "").replace('"', '').split()
    lines = []
    for i in range(0, len(words), 3):
        lines.append(" ".join(words[i:i+3]))
    drawtext = ""
    for i, line in enumerate(lines[:3]):
        y = 180 + i * 75
        if i > 0:
            drawtext += ","
        drawtext += f"drawtext=text='{line}':fontsize=55:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y={y}:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vf", drawtext,
        "-map", "0:v", "-map", "0:a",
        "-c:v", "libx264", "-b:v", "800k", "-c:a", "aac", "-b:a", "128k",
        "-preset", "fast", "-pix_fmt", "yuv420p", output_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        import shutil
        shutil.copy(video_path, output_path)

async def process_video(video_path, mascot_path="data/mascot.png"):
    os.makedirs("temp/clips", exist_ok=True)
    loop = asyncio.get_event_loop()
    
    total, w, h = get_video_info(video_path)
    logger.info(f"Тривалість: {total:.0f} сек, розмір: {w}x{h}")
    
    # Транскрипція через Whisper
    logger.info("Транскрибую аудіо через Whisper...")
    audio_path = "temp/audio.wav"
    await loop.run_in_executor(None, extract_audio, video_path, audio_path)
    segments = await transcribe_audio(audio_path)
    os.remove(audio_path)
    logger.info(f"Транскрипція готова, {len(segments)} сегментів")
    
    # GPT вибирає найкращі моменти
    logger.info("GPT аналізує моменти...")
    moments = await find_best_moments(segments, total)
    logger.info(f"GPT вибрав {len(moments)} моментів")
    
    ready_clips = []
    for i, (start, end) in enumerate(moments):
        try:
            duration = end - start
            v = f"temp/clips/clip_{i+1:02d}_v.mp4"
            m = f"temp/clips/clip_{i+1:02d}_m.mp4"
            f = f"temp/clips/clip_{i+1:02d}_final.mp4"
            
            await loop.run_in_executor(None, convert_to_vertical, video_path, v, start, duration)
            await loop.run_in_executor(None, add_mascot, v, m, mascot_path)
            
            segment_text = " ".join([s["text"] for s in segments if start <= s["start"] <= end])
            title = await generate_title(segment_text[:200])
            
            await loop.run_in_executor(None, add_title, m, f, title)
            ready_clips.append({"path": f, "title": title, "duration": duration})
            
            for tmp in [v, m]:
                if os.path.exists(tmp):
                    os.remove(tmp)
            logger.info(f"Кліп {i+1}/{len(moments)} готовий")
        except Exception as e:
            logger.error(f"Кліп {i+1} помилка: {e}")
    
    logger.info(f"Готово {len(ready_clips)} кліпів")
    return ready_clips
