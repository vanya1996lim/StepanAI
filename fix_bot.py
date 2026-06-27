with open('bot.py', 'r') as f:
    content = f.read()

old = """        await msg.edit_text(
            f'✅ Готово!\\n\\n'
            f'🎬 Нарізано роликів: {clip_count}\\n'
            f'📤 Опубліковано: {results[\"published\"]}\\n'
            f'❌ Помилок: {results[\"errors\"]}\\n\\n'
            f'Ролики розподілені по ФП протягом дня 🚀'
        )"""

new = """        await msg.edit_text(
            f'✅ Готово!\\n\\n'
            f'🎬 Нарізано роликів: {clip_count}\\n'
            f'📤 Опубліковано: {results[\"published\"]}\\n'
            f'❌ Помилок: {results[\"errors\"]}\\n\\n'
            f'Ролики розподілені по ФП протягом дня 🚀'
        )
        for clip in clips:
            if os.path.exists(clip['path']):
                await update.message.reply_video(open(clip['path'], 'rb'), caption=clip['title'])"""

if old in content:
    content = content.replace(old, new)
    with open('bot.py', 'w') as f:
        f.write(content)
    print('OK - replaced')
else:
    # Знаходимо де закінчується блок і додаємо після
    idx = content.find("Ролики розподілені по ФП протягом дня")
    print(f'NOT FOUND, context: {repr(content[idx:idx+200])}')
