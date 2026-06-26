import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from modules.downloader import download_video
from modules.processor import process_video
from modules.publisher import publish_to_all_pages
from modules.config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

config = Config()

# ===== КОМАНДИ =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Привіт! Я твій бот для автопублікації відео.\n\n"
        "📌 Що я вмію:\n"
        "• Качаю відео з YouTube / TikTok\n"
        "• Нарізаю на рілси з AI\n"
        "• Накладаю маскота і заголовок\n"
        "• Публікую на всі фанпейджі автоматично\n\n"
        "📎 Просто скинь посилання на відео або команду:\n"
        "/help — всі команди\n"
        "/status — статус черги\n"
        "/mascot — замінити маскота\n"
        "/pause — пауза публікацій\n"
        "/resume — відновити публікації"
    )
    await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 Всі команди:\n\n"
        "/start — головне меню\n"
        "/status — скільки відео в черзі\n"
        "/mascot — замінити маскота (надішли PNG)\n"
        "/pause — зупинити всі публікації\n"
        "/resume — відновити публікації\n"
        "/report — звіт по охвату\n"
        "/pages — список підключених ФП\n\n"
        "🎬 Щоб обробити відео — просто скинь посилання YouTube або TikTok"
    )
    await update.message.reply_text(text)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    queue_count = len(context.bot_data.get('queue', []))
    paused = context.bot_data.get('paused', False)
    status_text = "⏸ Пауза" if paused else "✅ Активний"
    await update.message.reply_text(
        f"📊 Статус бота: {status_text}\n"
        f"🎬 Відео в черзі: {queue_count}\n"
        f"📄 Підключено ФП: {len(config.facebook_pages)}"
    )

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data['paused'] = True
    await update.message.reply_text("⏸ Публікації призупинено. /resume щоб відновити.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.bot_data['paused'] = False
    await update.message.reply_text("▶️ Публікації відновлено!")

async def mascot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['waiting_mascot'] = True
    await update.message.reply_text(
        "🐱 Надішли новий PNG маскота з прозорим фоном.\n"
        "Він замінить поточного на всіх нових відео."
    )

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = context.bot_data.get('stats', {})
    total_published = stats.get('total_published', 0)
    total_reach = stats.get('total_reach', 0)
    ready_claims = stats.get('ready_claims', 0)

    await update.message.reply_text(
        f"📈 Звіт:\n\n"
        f"✅ Опубліковано всього: {total_published}\n"
        f"👁 Загальний охват: {total_reach:,}\n"
        f"💰 Готово до заявки: {ready_claims} відео\n"
    )

async def pages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not config.facebook_pages:
        await update.message.reply_text("❌ Немає підключених ФП. Додай їх в config.py")
        return
    text = "📄 Підключені фанпейджі:\n\n"
    for i, page in enumerate(config.facebook_pages, 1):
        text += f"{i}. {page['name']}\n"
    await update.message.reply_text(text)

# ===== ОБРОБКА ПОСИЛАНЬ =====

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Якщо чекаємо маскота
    if context.user_data.get('waiting_mascot') and message.photo:
        await handle_mascot_upload(update, context)
        return

    # Якщо це документ PNG (маскот)
    if context.user_data.get('waiting_mascot') and message.document:
        if message.document.mime_type == 'image/png':
            await handle_mascot_upload(update, context)
            return

    # Якщо це посилання на відео
    text = message.text or ""
    if any(domain in text for domain in ['youtube.com', 'youtu.be', 'tiktok.com']):
        await handle_video_link(update, context, text)
        return

    await message.reply_text("📎 Скинь посилання на YouTube або TikTok відео")

async def handle_mascot_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ Зберігаю маскота...")
    
    try:
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
        else:
            file = await update.message.document.get_file()
        
        mascot_path = "data/mascot.png"
        await file.download_to_drive(mascot_path)
        context.user_data['waiting_mascot'] = False
        await msg.edit_text("✅ Маскот оновлено! Всі нові відео будуть з ним.")
    except Exception as e:
        await msg.edit_text(f"❌ Помилка: {e}")

async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    if context.bot_data.get('paused'):
        await update.message.reply_text("⏸ Бот на паузі. /resume щоб відновити.")
        return

    msg = await update.message.reply_text(
        "⬇️ Завантажую відео...\n"
        "Це може зайняти 1-2 хвилини"
    )

    try:
        # Завантаження
        await msg.edit_text("⬇️ Завантажую відео...")
        video_path = await download_video(url)

        await msg.edit_text("✂️ AI нарізає відео на рілси...")
        clips = await process_video(video_path, mascot_path="data/mascot.png")

        clip_count = len(clips)
        await msg.edit_text(f"📤 Готово {clip_count} роликів! Публікую на ФП...")

        # Публікація
        results = await publish_to_all_pages(clips, config.facebook_pages, context)

        # Оновлення статистики
        stats = context.bot_data.get('stats', {})
        stats['total_published'] = stats.get('total_published', 0) + results['published']
        context.bot_data['stats'] = stats

        await msg.edit_text(
            f"✅ Готово!\n\n"
            f"🎬 Нарізано роликів: {clip_count}\n"
            f"📤 Опубліковано: {results['published']}\n"
            f"❌ Помилок: {results['errors']}\n\n"
            f"Ролики розподілені по ФП протягом дня 🚀"
        )

    except Exception as e:
        logger.error(f"Error processing video: {e}")
        await msg.edit_text(f"❌ Помилка при обробці відео:\n{e}")

# ===== ЗАПУСК =====

def main():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("Не знайдено TELEGRAM_BOT_TOKEN в змінних середовища")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("pause", pause))
    app.add_handler(CommandHandler("resume", resume))
    app.add_handler(CommandHandler("mascot", mascot_command))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("pages", pages))
    
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.Document.ALL, handle_message))

    logger.info("Бот запущено!")
    app.run_polling()

if __name__ == '__main__':
    main()
