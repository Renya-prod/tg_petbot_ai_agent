import csv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from services import database as db


CHOOSING_METHOD, MANUAL_INPUT, FILE_INPUT = range(3)


async def addposts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
    else:
        message = update.message

    if "selected_channel" not in context.user_data:
        await message.reply_text("⚠️ Сначала выберите канал командой /start")
        return ConversationHandler.END

    channel = context.user_data["selected_channel"]

    if isinstance(channel, dict):
        channel_name = channel["name"]
    else:
        channel_name = str(channel)

    keyboard = [
        [InlineKeyboardButton("✍ Вручную", callback_data="add_manual")],
        [InlineKeyboardButton("📂 Загрузить файл (.txt / .csv)", callback_data="add_file")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await message.reply_text(
        f"📝 *Добавление постов в канал:* '{channel_name}'\n\n"
        "Выберите способ добавления постов:\n"
        "• Вручную — вставляйте текст постов прямо в чат по одному сообщению.\n"
        "• Файл — загрузите .txt или .csv с постами, я их сохраню.\n\n"
        "После добавления не менее 3 постов, вы сможете создавать новые идеи и посты для этого канала.",
        reply_markup=reply_markup
    )
    return CHOOSING_METHOD


async def add_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("✅ Завершить", callback_data="done_manual")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "✍ Отправьте посты по одному сообщению.\n"
        "В конце можете указать стиль через 'Стиль: <название>' или оставьте по умолчанию.\n\n"
        "Когда закончите, нажмите кнопку ниже или отправьте /done",
        reply_markup=reply_markup
    )
    return MANUAL_INPUT


async def save_manual_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    channel = context.user_data["selected_channel"]
    text = update.message.text

    style = "ручной ввод"
    if "\nСтиль:" in text:
        parts = text.rsplit("\nСтиль:", 1)
        text = parts[0].strip()
        style = parts[1].strip()

    db.add_post(channel["channel_id"], "Пост придуман пользователем", style, text)

    await update.message.reply_text(
        f"✅ Пост сохранён в канал '{channel['name']}' со стилем '{style}'.\n\n"
        "Отправьте следующий пост или нажмите кнопку /done, чтобы завершить добавление."
    )

    return MANUAL_INPUT


async def done_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
            [KeyboardButton("/newpost"), KeyboardButton("/addposts")],
            [KeyboardButton("/back")]
        ]
    await update.message.reply_text(
        "✅ Добавление постов завершено.\n\n"
        "Теперь вы можете создать новый пост для этого канала /newpost \n"
        "Или вернуться в главное меню /back",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END


async def done_manual_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
            [KeyboardButton("/newpost"), KeyboardButton("/addposts")],
            [KeyboardButton("/back")]
        ]
    await update.message.reply_text(
        "✅ Добавление постов завершено.\n\n"
        "Теперь вы можете создать новый пост для этого канала /newpost \n"
        "Или вернуться в главное меню /back",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END


async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "📂 Пришлите файл .txt или .csv.\n\n"
        "▪ В .txt посты считываются следующим образом: \n"
            '   Пост:\n' 
            "   'текст первого поста'\n"
            '   Стиль:\n'
            "   'стиль первого поста'\n"
            '   Пост:\n' 
            "   'текст второго поста'\n"
            '   и т.д. по аналогии...\n\n'
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
            content = f.read()

        blocks = content.split("Пост:")
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            if "Стиль:" in block:
                text_part, style_part = block.split("Стиль:", 1)
                text = text_part.strip().strip('"')
                style = style_part.strip().strip('"')
            else:
                text = block.strip().strip('"')
                style = "ручной ввод"

            if text:
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

    keyboard = [
            [KeyboardButton("/newpost"), KeyboardButton("/addposts")],
            [KeyboardButton("/back")]
        ]

    await update.message.reply_text(
        f"✅ Загружено {saved_posts} постов в канал '{channel['name']}'."
        "Теперь вы можете создать новый пост для этого канала или вернуться в главное меню.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return ConversationHandler.END


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

    app.add_handler(conv_handler, group=0)
