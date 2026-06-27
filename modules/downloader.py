import yt_dlp
import os
import asyncio
import logging
import random

logger = logging.getLogger(__name__)

PROXIES = [
    "http://liejdvlv:c44vg83ye651@31.59.20.176:6754",
    "http://liejdvlv:c44vg83ye651@31.56.127.193:7684",
    "http://liejdvlv:c44vg83ye651@45.38.107.97:6014",
    "http://liejdvlv:c44vg83ye651@38.154.203.95:5863",
    "http://liejdvlv:c44vg83ye651@198.105.121.200:6462",
    "http://liejdvlv:c44vg83ye651@64.137.96.74:6641",
    "http://liejdvlv:c44vg83ye651@198.23.243.226:6361",
    "http://liejdvlv:c44vg83ye651@38.154.185.97:6370",
    "http://liejdvlv:c44vg83ye651@142.111.67.146:5611",
    "http://liejdvlv:c44vg83ye651@191.96.254.138:6185",
]

async def download_video(url: str) -> str:
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    proxy = random.choice(PROXIES)
    logger.info(f"Використовую проксі: {proxy}")

    ydl_opts = {
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",
        "format": "bestvideo[height<=720]+bestaudio/best",
        "proxy": proxy,
        "cookiefile": "data/cookies.txt",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info["id"]
            path = f"{output_dir}/{video_id}.mp4"
            if not os.path.exists(path):
                for f in os.listdir(output_dir):
                    if f.startswith(video_id):
                        return f"{output_dir}/{f}"
            return path

    loop = asyncio.get_event_loop()
    video_path = await loop.run_in_executor(None, _download)
    logger.info(f"Відео завантажено: {video_path}")
    return video_path
