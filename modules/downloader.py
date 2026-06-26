import os
import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "a389fce096mshcb0341ae8ba5075p1b91cejsn17a50795028c")

async def download_video(url: str) -> str:
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        # Download All in One API
        api_url = "https://download-all-in-one.p.rapidapi.com/v1/download"
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": "download-all-in-one.p.rapidapi.com",
            "Content-Type": "application/json"
        }
        payload = {"url": url}

        async with session.post(api_url, json=payload, headers=headers) as resp:
            data = await resp.json()
            logger.info(f"API response: {data}")

        # Отримуємо пряме посилання на відео
        video_url = None
        if isinstance(data, dict):
            video_url = (data.get("url") or data.get("download_url") or 
                        data.get("video_url") or data.get("link"))
            if not video_url and data.get("medias"):
                medias = data["medias"]
                if isinstance(medias, list) and medias:
                    video_url = medias[0].get("url") or medias[0].get("link")

        if not video_url:
            raise ValueError(f"Не вдалось отримати посилання на відео: {data}")

        # Завантажуємо відео
        video_path = f"{output_dir}/video_{hash(url)}.mp4"
        async with session.get(video_url) as video_resp:
            with open(video_path, "wb") as f:
                async for chunk in video_resp.content.iter_chunked(8192):
                    f.write(chunk)

    logger.info(f"Відео завантажено: {video_path}")
    return video_path
