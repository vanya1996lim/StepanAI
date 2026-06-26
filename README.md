# 🐱 CAT BET Bot — Інструкція налаштування

## Що потрібно перед запуском

### 1. Telegram Bot Token
1. Відкрий Telegram → знайди @BotFather
2. Напиши `/newbot`
3. Дай назву боту
4. Скопіюй токен (виглядає як `7123456789:AAHxxx...`)

### 2. OpenAI API Key (для заголовків)
1. Зайди на platform.openai.com
2. API Keys → Create new secret key
3. Скопіюй ключ

### 3. Facebook токени для кожного ФП
1. Зайди на developers.facebook.com
2. My Apps → Create App → Business
3. Додай продукт "Pages API"
4. Graph API Explorer → вибери свою сторінку
5. Запроси права: `pages_manage_posts`, `pages_read_engagement`
6. Скопіюй Page ID і Access Token для кожної сторінки

---

## Налаштування

### Крок 1 — Заповни config.py
Відкрий `modules/config.py` і заповни:
```python
self.facebook_pages = [
    {
        "name": "Назва сторінки 1",
        "page_id": "123456789",        # Page ID з Facebook
        "access_token": "EAAxxxxxxx"   # Access Token
    },
    # ... всі 20 сторінок
]
```

### Крок 2 — Завантаж маскота
Покладіть PNG маскота з прозорим фоном в папку `data/mascot.png`
Або надішли його боту командою `/mascot`

---

## Запуск на Railway (хмара)

1. Зареєструйся на railway.app
2. New Project → Deploy from GitHub або Upload
3. Завантаж папку з кодом
4. Variables → додай:
   - `TELEGRAM_BOT_TOKEN` = твій токен
   - `OPENAI_API_KEY` = твій ключ OpenAI
5. Deploy → бот запущено!

---

## Команди бота

| Команда | Що робить |
|---------|-----------|
| `/start` | Головне меню |
| `/status` | Статус і черга |
| `/mascot` | Замінити маскота |
| `/pause` | Зупинити публікації |
| `/resume` | Відновити публікації |
| `/report` | Звіт по охвату |
| `/pages` | Список ФП |

## Як використовувати

1. Запусти бота
2. Скинь посилання на YouTube або TikTok відео
3. Бот сам нарізає, обробляє і публікує на всі ФП
4. Отримай звіт вранці

---

## Структура проекту
```
catbet_bot/
├── bot.py              # Головний файл
├── requirements.txt    # Залежності
├── modules/
│   ├── config.py       # Налаштування
│   ├── downloader.py   # Завантаження відео
│   ├── processor.py    # Обробка відео
│   └── publisher.py    # Публікація на Facebook
├── data/
│   └── mascot.png      # Твій маскот
└── temp/               # Тимчасові файли (створюється автоматично)
```
