import yt_dlp
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

async def download_video(url: str) -> str:
    """Завантажує відео з YouTube або TikTok. Повертає шлях до файлу."""
    
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        'outtmpl': f'{output_dir}/%(id)s.%(ext)s',
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        # Для TikTok — обходимо захист
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    }

    def _download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            ext = info.get('ext', 'mp4')
            return f"{output_dir}/{video_id}.{ext}"

    # Запускаємо в окремому потоці щоб не блокувати бота
    loop = asyncio.get_event_loop()
    video_path = await loop.run_in_executor(None, _download)

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Відео не завантажилось: {video_path}")

    logger.info(f"Відео завантажено: {video_path}")
    return video_path


async def get_account_videos(account_url: str, min_views: int = 30000) -> list:
    """
    Отримує список відео з акаунту TikTok/YouTube
    з фільтром по переглядах (поки базова версія — повертає всі відео акаунту)
    """
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,  # Тільки метадані, без завантаження
        'playlistend': 50,     # Беремо останні 50 відео
    }

    def _get_list():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(account_url, download=False)
            entries = info.get('entries', [])
            videos = []
            for entry in entries:
                view_count = entry.get('view_count', 0) or 0
                if view_count >= min_views:
                    videos.append({
                        'url': entry.get('url') or entry.get('webpage_url'),
                        'title': entry.get('title', ''),
                        'views': view_count,
                        'duration': entry.get('duration', 0)
                    })
            return videos

    loop = asyncio.get_event_loop()
    videos = await loop.run_in_executor(None, _get_list)
    logger.info(f"Знайдено {len(videos)} відео з {min_views}+ переглядів")
    return videos
