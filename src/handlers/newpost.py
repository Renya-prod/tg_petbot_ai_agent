# handlers/newpost.py

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from services import database as db
from services.llm import generate_post_ideas, generate_post_draft

# Состояния ConversationHandler
CHOOSING_IDEA, CHOOSING_STYLE = range(2)


# ----------------------
# Старт команды /newpost
# ----------------------
async def newpost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "selected_channel" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала выберите канал командой /start")
        return ConversationHandler.END

    # Проверяем, что selected_channel — это словарь, если нет, ищем по имени
    channel = context.user_data["selected_channel"]
    if isinstance(channel, dict):
        channel_id, channel_name = channel["channel_id"], channel["name"]
    else:
        channel_name = str(channel)
        channels = db.get_channels_by_name(channel_name)
        if not channels:
            await update.message.reply_text("❌ Канал не найден")
            return ConversationHandler.END
        channel_id, channel_name = channels[0]["channel_id"], channels[0]["name"]
        context.user_data["selected_channel"] = channels[0]  # сохраняем словарь

    # Берём последние 5 постов из базы
    posts = db.get_last_posts(channel_id, limit=5)
    if not posts:
        await update.message.reply_text("❗ В этом канале пока нет постов для примера.")
        return ConversationHandler.END

    # Генерация идей через Gigachat
    ideas = await generate_post_ideas([p["text"] for p in posts])
    context.user_data["post_ideas"] = ideas

    # Строим кнопки для выбора идей
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {idea['idea']}", callback_data=f"idea_{i}")]
        for i, idea in enumerate(ideas)
    ]
    keyboard.append([InlineKeyboardButton("✏ Ввести свою тему", callback_data="custom")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Выберите идею для нового поста в канале '{channel_name}':",
        reply_markup=reply_markup,
    )
    return CHOOSING_IDEA


# ----------------------
# Выбор идеи
# ----------------------
async def choose_idea(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "custom":
        await query.message.reply_text("✏ Введите свою тему для поста:")
        context.user_data["custom_idea"] = True
        return CHOOSING_IDEA

    idx = int(data.replace("idea_", ""))
    selected = context.user_data["post_ideas"][idx]
    context.user_data["selected_idea"] = selected["idea"]
    context.user_data["available_styles"] = selected["styles"]

    return await show_styles(query, context)


# ----------------------
# Обработка кастомной идеи
# ----------------------
async def custom_idea_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("custom_idea"):
        return ConversationHandler.END

    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Тема не может быть пустой, попробуйте ещё раз:")
        return CHOOSING_IDEA

    context.user_data["selected_idea"] = text
    context.user_data["available_styles"] = ["Юмористический", "Серьёзный", "Информационный"]
    return await show_styles(update, context)


# ----------------------
# Показ кнопок выбора стиля
# ----------------------
async def show_styles(update_or_query, context):
    styles = context.user_data.get("available_styles", [])
    keyboard = [
        [InlineKeyboardButton(style, callback_data=f"style_{style}")]
        for style in styles
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Проверяем тип объекта
    if hasattr(update_or_query, "message"):  # CallbackQuery
        await update_or_query.message.reply_text(
            "Выберите стиль поста:", reply_markup=reply_markup
        )
    else:  # Update
        await update_or_query.effective_message.reply_text(
            "Выберите стиль поста:", reply_markup=reply_markup
        )
    return CHOOSING_STYLE

# ----------------------
# Выбор стиля и генерация поста
# ----------------------
async def choose_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Получаем выбранный стиль
    style = query.data.replace("style_", "")
    context.user_data["selected_style"] = style

    # Получаем канал и идею безопасно
    channel = context.user_data.get("selected_channel")
    if isinstance(channel, dict):
        channel_id, channel_name = channel["channel_id"], channel["name"]
    else:
        channel_name = str(channel)
        channels = db.get_channels_by_name(channel_name)
        if not channels:
            await query.message.reply_text("❌ Канал не найден")
            return ConversationHandler.END
        channel_id, channel_name = channels[0]["channel_id"], channels[0]["name"]
        context.user_data["selected_channel"] = channels[0]

    idea = context.user_data["selected_idea"]

    # Генерация черновика через Gigachat с последними 5 постами
    posts = db.get_last_posts(channel_id, limit=5)
    draft = await generate_post_draft(channel_name, idea, style, [p["text"] for p in posts])
    context.user_data["draft_post"] = draft

    # Отправляем пользователю готовый черновик
    await query.message.reply_text(f"✅ Черновик готов!\n\n{draft}")

    # Сохраняем пост в базу
    db.add_post(channel_id, idea, style, draft)

    return ConversationHandler.END


# ----------------------
# Регистрация хендлеров
# ----------------------
def setup_newpost_handlers(app):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newpost", newpost_command)],
        states={
            CHOOSING_IDEA: [
                CallbackQueryHandler(choose_idea, pattern="^idea_"),
                CallbackQueryHandler(choose_idea, pattern="^custom$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_idea_input),
            ],
            CHOOSING_STYLE: [
                CallbackQueryHandler(choose_style, pattern="^style_"),
            ],
        },
        fallbacks=[CommandHandler("start", lambda u, c: None)],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)

