# handlers/addposts.py

import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from services import database as db

# Состояния для ConversationHandler
CHOOSING_METHOD, MANUAL_INPUT, FILE_INPUT = range(3)


# ----------------------
# Старт добавления постов
# ----------------------
async def addposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "selected_channel" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала выберите канал командой /start")
        return ConversationHandler.END

    channel = context.user_data["selected_channel"]

    keyboard = [
        [InlineKeyboardButton("✍ Вручную", callback_data="add_manual")],
        [InlineKeyboardButton("📂 Загрузить файл (.txt / .csv)", callback_data="add_file")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Добавление постов в канал: {channel['name']}",
        reply_markup=reply_markup
    )
    return CHOOSING_METHOD


# ----------------------
# Ручной ввод
# ----------------------
async def add_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data="done_manual")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "✍ Отправьте посты по одному.\n"
        "В конце укажите стиль через 'Стиль: <название>' или оставьте по умолчанию.\n\n"
        "Когда закончите, нажмите кнопку ниже или отправьте /done",
        reply_markup=reply_markup
    )
    return MANUAL_INPUT


async def save_manual_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = context.user_data["selected_channel"]
    text = update.message.text

    # Разбор стиля
    style = "ручной ввод"
    if "\nСтиль:" in text:
        parts = text.rsplit("\nСтиль:", 1)
        text = parts[0].strip()
        style = parts[1].strip()

    # Сохраняем в БД
    db.add_post(channel["channel_id"], "Пост придуман пользователем", style, text)

    # Подтверждение
    await update.message.reply_text(
        f"✅ Пост сохранён в канал '{channel['name']}' со стилем '{style}'.\n"
        "Отправьте следующий пост или нажмите ✅ Завершить."
    )

    return MANUAL_INPUT


async def done_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Добавление постов завершено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def done_manual_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("✅ Добавление постов завершено.")
    return ConversationHandler.END


# ----------------------
# Загрузка файла
# ----------------------
async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "📂 Пришлите файл .txt или .csv.\n\n"
        "▪ В .txt каждая строка — отдельный пост.\n"
        "▪ В .csv первая колонка — текст, вторая (необязательно) — стиль."
    )
    return FILE_INPUT


def parse_line_style(line: str):
    style = "ручной ввод"
    if "Стиль:" in line:
        parts = line.rsplit("Стиль:", 1)
        text = parts[0].strip()
        style = parts[1].strip()
    else:
        text = line.strip()
    return text, style


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = context.user_data["selected_channel"]
    document = update.message.document
    if not document:
        await update.message.reply_text("⚠️ Файл не найден.")
        return FILE_INPUT

    file = await document.get_file()
    file_path = await file.download_to_drive()

    saved_posts = 0
    if document.file_name.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    text, style = parse_line_style(line)
                    db.add_post(channel["channel_id"], "Пост придуман пользователем", style, text)
                    saved_posts += 1
    elif document.file_name.endswith(".csv"):
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    if len(row) == 1:
                        text, style = parse_line_style(row[0])
                    else:
                        text, style = row[0], row[1]
                    db.add_post(channel["channel_id"], "Пост придуман пользователем", style, text.strip())
                    saved_posts += 1
    else:
        await update.message.reply_text("⚠️ Поддерживаются только .txt и .csv файлы")
        return FILE_INPUT

    await update.message.reply_text(f"✅ Загружено {saved_posts} постов в канал '{channel['name']}'.")
    return ConversationHandler.END


# ----------------------
# Регистрация хендлеров
# ----------------------
def setup_addposts_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("addposts", addposts_command)],
        states={
            CHOOSING_METHOD: [
                CallbackQueryHandler(add_manual, pattern="^add_manual$"),
                CallbackQueryHandler(add_file, pattern="^add_file$"),
            ],
            MANUAL_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_manual_post),
                CommandHandler("done", done_manual),
                CallbackQueryHandler(done_manual_button, pattern="^done_manual$"),
            ],
            FILE_INPUT: [
                MessageHandler(filters.Document.ALL, handle_file),
            ],
        },
        fallbacks=[CommandHandler("start", lambda u, c: None)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler, group=0)  # <<< группа 0
