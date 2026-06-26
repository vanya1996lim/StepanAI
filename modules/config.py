import os

class Config:
    def __init__(self):
        # Telegram
        self.telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')

        # OpenAI для генерації заголовків
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')

        # Скільки секунд мінімум / максимум для кліпу
        self.clip_min_duration = 30
        self.clip_max_duration = 90

        # Скільки кліпів максимум з одного відео
        self.max_clips_per_video = 20

        # Ліміт публікацій на день на один ФП
        self.max_posts_per_page_per_day = 5

        # Мінімальний інтервал між постами (секунди) = 2 години
        self.min_interval_between_posts = 7200

        # Facebook сторінки — заповни своїми даними
        self.facebook_pages = [
            # {
            #     "name": "Назва сторінки 1",
            #     "page_id": "123456789",
            #     "access_token": "EAAxxxxxxx"
            # },
            # Додай всі 20 сторінок тут
        ]

        # Чорний список слів (якщо в заголовку є — пропускаємо)
        self.blacklist_words = [
            # "слово1", "слово2"
        ]
