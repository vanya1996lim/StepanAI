import os
import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = "a389fce096mshcb0341ae8ba5075p1b91cejsn17a50795028c"

async def download_video(url: str) -> str:
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "social-media-video-downloader.p.rapidapi.com"
        }

        # Отримуємо інфо про відео
        api_url = "https://social-media-video-downloader.p.rapidapi.com/smvd/get/all"
        params = {"url": url}

        async with session.get(api_url, headers=headers, params=params) as resp:
            data = await resp.json()
            logger.info(f"API response keys: {list(data.keys()) if isinstance(data, dict) else data}")

        # Шукаємо пряме посилання на відео
        video_url = None
        if isinstance(data, dict):
            links = data.get("links", [])
            if links:
                for link in links:
                    if isinstance(link, dict) and link.get("quality") in ["720p", "480p", "360p", "hd", "sd"]:
                        video_url = link.get("link")
                        break
                if not video_url and links:
                    video_url = links[0].get("link") if isinstance(links[0], dict) else links[0]

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
