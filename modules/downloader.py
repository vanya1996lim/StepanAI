import yt_dlp
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

async def download_video(url: str) -> str:
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            ext = info.get('ext', 'mp4')
            path = f"{output_dir}/{video_id}.{ext}"
            if not os.path.exists(path):
                for f in os.listdir(output_dir):
                    if f.startswith(video_id):
                        return f"{output_dir}/{f}"
            return path

    loop = asyncio.get_event_loop()
    video_path = await loop.run_in_executor(None, _download)
    logger.info(f"Відео завантажено: {video_path}")
    return video_path
