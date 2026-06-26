import os
import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = "a389fce096mshcb0341ae8ba5075p1b91cejsn17a50795028c"

async def download_video(url: str) -> str:
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    # Витягуємо video ID з YouTube URL
    video_id = url
    if "youtube.com" in url or "youtu.be" in url:
        if "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]

    async with aiohttp.ClientSession() as session:
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "youtube-media-downloader.p.rapidapi.com"
        }

        params = {
            "videoId": video_id,
            "urlAccess": "normal",
            "videos": "auto",
            "audios": "auto"
        }

        async with session.get(
            "https://youtube-media-downloader.p.rapidapi.com/v2/video/details",
            headers=headers, params=params
        ) as resp:
            data = await resp.json()
            logger.info(f"API keys: {list(data.keys()) if isinstance(data, dict) else data}")

        # Шукаємо відео посилання
        video_url = None
        videos = data.get("videos", {})
        if isinstance(videos, dict):
            items = videos.get("items", [])
            for v in items:
                if isinstance(v, dict) and v.get("height", 9999) <= 720:
                    video_url = v.get("url")
                    break

        if not video_url:
            raise ValueError(f"Не вдалось отримати посилання: {data}")

        # Завантажуємо відео
        video_path = f"{output_dir}/video_{abs(hash(url))}.mp4"
        async with session.get(video_url) as video_resp:
            with open(video_path, "wb") as f:
                async for chunk in video_resp.content.iter_chunked(8192):
                    f.write(chunk)

    logger.info(f"Відео завантажено: {video_path}")
    return video_path
