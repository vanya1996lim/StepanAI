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
        'format': 'best',
        'cookiefile': 'data/cookies.txt',
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
