from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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
from handlers import addposts

CHOOSING_IDEA, CHOOSING_STYLE, CONFIRM_DRAFT = range(3)


async def newpost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "selected_channel" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала выберите канал в главном меню")
        return ConversationHandler.END

    channel = context.user_data["selected_channel"]
    if isinstance(channel, dict):
        channel_id, channel_name = channel["channel_id"], channel["name"]
    else:
        channels = db.get_channels_by_name(str(channel))
        if not channels:
            await update.message.reply_text("❌ Канал не найден")
            return ConversationHandler.END
        channel_id, channel_name = channels[0]["channel_id"], channels[0]["name"]
        context.user_data["selected_channel"] = channels[0]

    posts = db.get_last_posts(channel_id, limit=5)
    if len(posts) < 3:
        await update.message.reply_text(
            f"⚠️ В этом канале недостаточно примеров (найдено {len(posts)}).\n"
            "Для генерации идей нужно минимум 3 поста.\n"
            "Нажмите /addposts, чтобы сразу добавить посты."
        )
        return ConversationHandler.END

    ideas = await generate_post_ideas([p["text"] for p in posts])
    context.user_data["post_ideas"] = ideas

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


async def show_styles(update_or_query, context):
    styles = context.user_data.get("available_styles", [])
    keyboard = [
        [InlineKeyboardButton(style, callback_data=f"style_{style}")]
        for style in styles
    ]
    keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="back_to_ideas")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update_or_query, "message"):
        await update_or_query.message.reply_text("Выберите стиль поста:", reply_markup=reply_markup)
    else:
        await update_or_query.effective_message.reply_text("Выберите стиль поста:", reply_markup=reply_markup)
    return CHOOSING_STYLE


async def back_to_ideas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ideas = context.user_data.get("post_ideas", [])
    keyboard = [
        [InlineKeyboardButton(f"{i+1}. {idea['idea']}", callback_data=f"idea_{i}")]
        for i, idea in enumerate(ideas)
    ]
    keyboard.append([InlineKeyboardButton("✏ Ввести свою тему", callback_data="custom")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text("⬅ Вернулись к выбору идеи:", reply_markup=reply_markup)
    return CHOOSING_IDEA


async def choose_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    style = query.data.replace("style_", "")
    context.user_data["selected_style"] = style

    channel = context.user_data.get("selected_channel")
    if isinstance(channel, dict):
        channel_id, channel_name = channel["channel_id"], channel["name"]
    else:
        channels = db.get_channels_by_name(str(channel))
        if not channels:
            await query.message.reply_text("❌ Канал не найден")
            return ConversationHandler.END
        channel_id, channel_name = channels[0]["channel_id"], channels[0]["name"]
        context.user_data["selected_channel"] = channels[0]

    idea = context.user_data["selected_idea"]
    posts = db.get_last_posts(channel_id, limit=5)
    draft = await generate_post_draft(channel_name, idea, style, [p["text"] for p in posts])
    context.user_data["draft_post"] = draft

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_draft")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back_to_styles")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(f"✅ Черновик готов!\n\n{draft}", reply_markup=reply_markup)
    return CONFIRM_DRAFT


async def back_to_styles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await show_styles(query, context)


async def confirm_draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    channel = context.user_data["selected_channel"]
    if isinstance(channel, dict):
        channel_id = channel["channel_id"]
    else:
        channel_id = db.get_channels_by_name(str(channel))[0]["channel_id"]

    idea = context.user_data["selected_idea"]
    style = context.user_data["selected_style"]
    draft = context.user_data["draft_post"]

    db.add_post(channel_id, idea, style, draft)
    await query.message.reply_text("💾 Черновик успешно сохранён!")

    return ConversationHandler.END

async def addposts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await addposts.addposts_command(update, context)


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
                CallbackQueryHandler(back_to_ideas, pattern="^back_to_ideas$"),
            ],
            CONFIRM_DRAFT: [
                CallbackQueryHandler(confirm_draft, pattern="^confirm_draft$"),
                CallbackQueryHandler(back_to_styles, pattern="^back_to_styles$"),
            ],
        },
        fallbacks=[CommandHandler("start", lambda u, c: None)],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
