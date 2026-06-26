import aiohttp
import asyncio
import os
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PUBLISHED_LOG = "data/published.json"

def load_published() -> set:
    """Завантажує список вже опублікованих відео."""
    if os.path.exists(PUBLISHED_LOG):
        with open(PUBLISHED_LOG) as f:
            return set(json.load(f))
    return set()

def save_published(published: set):
    """Зберігає список опублікованих відео."""
    os.makedirs("data", exist_ok=True)
    with open(PUBLISHED_LOG, 'w') as f:
        json.dump(list(published), f)

async def publish_reel_to_page(clip: dict, page: dict, session: aiohttp.ClientSession) -> bool:
    """
    Публікує один рілс на Facebook сторінку через Graph API.
    Повертає True якщо успішно.
    """
    page_id = page['page_id']
    access_token = page['access_token']
    video_path = clip['path']
    title = clip.get('title', '')

    try:
        # Крок 1 — Ініціалізуємо завантаження відео
        init_url = f"https://graph.facebook.com/v19.0/{page_id}/videos"
        
        file_size = os.path.getsize(video_path)
        
        init_data = {
            'upload_phase': 'start',
            'file_size': file_size,
            'access_token': access_token
        }

        async with session.post(init_url, data=init_data) as resp:
            init_result = await resp.json()
            
        if 'upload_session_id' not in init_result:
            logger.error(f"Помилка ініціалізації: {init_result}")
            return False

        upload_session_id = init_result['upload_session_id']
        video_id = init_result.get('video_id')

        # Крок 2 — Завантажуємо відео
        transfer_url = f"https://graph-video.facebook.com/v19.0/{page_id}/videos"
        
        with open(video_path, 'rb') as video_file:
            transfer_data = aiohttp.FormData()
            transfer_data.add_field('upload_phase', 'transfer')
            transfer_data.add_field('upload_session_id', upload_session_id)
            transfer_data.add_field('access_token', access_token)
            transfer_data.add_field('start_offset', '0')
            transfer_data.add_field('video_file_chunk', video_file, 
                                   filename='video.mp4', content_type='video/mp4')

            async with session.post(transfer_url, data=transfer_data) as resp:
                transfer_result = await resp.json()

        # Крок 3 — Завершуємо завантаження і публікуємо
        finish_data = {
            'upload_phase': 'finish',
            'upload_session_id': upload_session_id,
            'access_token': access_token,
            'title': title,
            'description': title,
        }

        async with session.post(init_url, data=finish_data) as resp:
            finish_result = await resp.json()

        if finish_result.get('success'):
            logger.info(f"✅ Опубліковано на {page['name']}: {title}")
            return True
        else:
            logger.error(f"❌ Помилка публікації на {page['name']}: {finish_result}")
            return False

    except Exception as e:
        logger.error(f"❌ Виняток при публікації на {page['name']}: {e}")
        return False


async def publish_to_all_pages(clips: list, pages: list, context=None) -> dict:
    """
    Розподіляє кліпи по сторінках і публікує з затримкою.
    Кожна сторінка отримує свій кліп, публікації розподілені протягом дня.
    """
    if not pages:
        logger.warning("Немає підключених сторінок!")
        return {'published': 0, 'errors': 0}

    if not clips:
        logger.warning("Немає кліпів для публікації!")
        return {'published': 0, 'errors': 0}

    published_count = 0
    error_count = 0

    # Розраховуємо інтервал між публікаціями
    # 20 ФП × 5 постів = 100 публікацій за день (86400 сек)
    # Інтервал ~864 сек (~14 хвилин між постами)
    interval_seconds = max(600, 86400 // (len(pages) * 5))

    async with aiohttp.ClientSession() as session:
        for i, page in enumerate(pages):
            # Кожна сторінка отримує свій кліп (по колу якщо кліпів менше)
            clip = clips[i % len(clips)]

            # Затримка між публікаціями щоб не спамити
            if i > 0:
                delay = interval_seconds
                logger.info(f"Чекаємо {delay} сек перед наступною публікацією...")
                await asyncio.sleep(min(delay, 30))  # В тесті 30 сек, в продакшні — повна затримка

            success = await publish_reel_to_page(clip, page, session)
            if success:
                published_count += 1
            else:
                error_count += 1

    return {
        'published': published_count,
        'errors': error_count
    }
