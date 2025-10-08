from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from services import database as db


def main_menu_reply():
    keyboard = [
        [KeyboardButton("/choose_channel")],
        [KeyboardButton("/add_channel")],
        [KeyboardButton("/delete_channel")],
        [KeyboardButton("/newpost")], 
        [KeyboardButton("/addposts")],
        [KeyboardButton("/help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    db_user = db.get_user(user.id)

    context.user_data.clear()

    if not db_user:
        db.add_user(user.id, user.username)

        await update.message.reply_text(
            f"👋 Привет, {user.username}!\n\n"
            "Я — твой AI-помощник, который помогает **создавать посты для твоих каналов** в Telegram.\n\n"
            "📘 *Важно:* сейчас мне не нужно быть добавленным в настоящий канал. Просто придумай или создай название канала — я буду сохранять все посты, которые мы с тобой создадим, и подбирать новые идеи в его стиле.\n\n"
            "🪄 Чтобы начать:\n"
            "1️⃣ Введи /add_channel — чтобы добавить свой первый канал (придумай название сам)\n"
            "2️⃣ Затем используй /newpost — чтобы я предложил идею и помог оформить текст\n\n"
            "Если что-то непонятно — набери /help.",
            reply_markup=main_menu_reply()
        )

    else:
        await update.message.reply_text(
            f"👋 Привет, {user.username}!\n\n"
            "Рад снова тебя видеть. 😊\n\n"
            "Выбери канал, с которым хочешь работать:\n"
            "👉 /choose_channel — выбрать из существующих\n\n"
            "Если у тебя пока нет каналов, просто добавь новый:\n"
            "➕ /add_channel — создать канал (можно придумать любое название)\n\n"
            "💡 После выбора канала используй /newpost, чтобы я предложил идею и помог оформить пост.",
            reply_markup=main_menu_reply()
        )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Справка по командам*\n\n"
        "Вот как со мной работать 👇\n\n"
        "• 🧭 /choose_channel — выбрать один из уже созданных каналов. Используй, если ты хочешь продолжить работу с темой, которую создавал ранее.\n\n"
        "• ➕ /add_channel — создать новый канал (можно просто придумать название). Я буду хранить все посты по этому названию и подбирать идеи в нужном стиле.\n\n"
        "• 🗑 /delete_channel — удалить канал из списка, если он больше не нужен.\n\n"
        "• ✍️ /newpost — создать новый пост. Я предложу идеи и помогу оформить текст под стиль выбранного канала.\n\n"
        "• 📥 /addposts — добавить примеры старых постов вручную. Это нужно, если хочешь, чтобы я лучше понимал стиль канала.\n\n"
        "• 🔙 /back — вернуться в главное меню.\n\n"
        "📘 *Важно:* тебе не нужно добавлять меня в настоящий Telegram-канал. Просто придумывай названия каналов — я буду хранить для них историю постов и помогать с новыми идеями. А ты уже скопируешь и вставишь в свой настоящий самостоятельно(пока что так, сорян).\n\n"
        "💡 *Совет:* начни с /add_channel, чтобы создать свой первый канал, а затем используй /newpost."
    )


async def add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_channel_name"] = True

    await update.message.reply_text(
        "🆕 Введи название для своего канала.\n\n"
        "Это не настоящий Telegram-канал — просто придумай любое имя, например *«Анекдоты»* или *«Путешествия»*.\n"
        "Я буду сохранять посты по этому названию и помогать писать новые в том же стиле. А ты уже скопируешь и вставишь в свой настоящий самостоятельно.\n\n"
        "✏️ Напиши название канала ниже:",
        reply_markup=main_menu_reply()
    )


async def delete_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_user(user.id)
    channels = db.get_channels(db_user["user_id"])

    if not channels:
        await update.message.reply_text(
            "❗ У вас пока нет каналов для удаления.",
            reply_markup=main_menu_reply()
        )
        return
    
    channel_names = [ch["name"] for ch in channels]
    keyboard = [[KeyboardButton(name)] for name in channel_names]
    keyboard.append([KeyboardButton("/back")])

    context.user_data["awaiting_channel_deletion"] = True

    await update.message.reply_text(
        "Выберите канал для удаления:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def choose_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_user(user.id)
    channels = db.get_channels(db_user["user_id"])

    if not channels:
        await update.message.reply_text(
            "❗ У вас пока нет каналов. Сначала добавьте канал через /add_channel.",
            reply_markup=main_menu_reply()
        )
        return

    channel_names = [ch["name"] for ch in channels]
    keyboard = [[KeyboardButton(name)] for name in channel_names]
    keyboard.append([KeyboardButton("/back")])

    context.user_data["awaiting_channel_selection"] = True

    await update.message.reply_text(
        "📂 Выберите канал для работы в меню. \n"
        " Это одно из названий каналов, которые вы создали.\n Нажмите на меню ниже 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


async def back_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("↩ Возврат в главное меню", reply_markup=main_menu_reply())


async def text_parser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_user(user.id)
    text = update.message.text.strip()

    if context.user_data.get("awaiting_channel_name"):
        db.add_channel(db_user["user_id"], text)
        context.user_data["awaiting_channel_name"] = False
        await update.message.reply_text(
            f"✅ Канал '{text}' добавлен!\n\n"
            "Теперь вы можете:\n"
            "• /choose_channel — выбрать этот канал для работы и создавать посты\n"
            "• /add_channel — добавить ещё один канал, если хотите разделять темы\n\n"
            "💡 После выбора канала используйте /newpost, чтобы я предложил идеи и помог написать пост в стиле этого канала.",
            reply_markup=main_menu_reply()
        )

        return

    if context.user_data.get("awaiting_channel_deletion"):
        channels = db.get_channels(db_user["user_id"])
        channel = next((ch for ch in channels if ch["name"] == text), None)
        if not channel:
            await update.message.reply_text("❌ Канал не найден, попробуйте снова.")
            return

        db.delete_channel(db_user["user_id"], channel["name"])
        context.user_data["awaiting_channel_deletion"] = False

        await update.message.reply_text(
            f"🗑 Канал '{text}' удалён!",
            reply_markup=main_menu_reply()
        )
        return

    if context.user_data.get("awaiting_channel_selection"):
        channels = db.get_channels(db_user["user_id"])
        channel = next((ch for ch in channels if ch["name"] == text), None)
        if not channel:
            await update.message.reply_text("❌ Канал не найден, попробуйте снова.")
            return

        context.user_data["selected_channel"] = channel
        context.user_data["awaiting_channel_selection"] = False

        keyboard = [
            [KeyboardButton("/newpost"), KeyboardButton("/addposts")],
            [KeyboardButton("/back")]
        ]

        await update.message.reply_text(
            f"✅ Выбран канал *{text}*.\nТеперь вы можете использовать /newpost или /addposts из меню.",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode="Markdown"
        )

        return

    await update.message.reply_text("❗ Пожалуйста, используйте кнопки или команды для взаимодействия.")


def setup_start_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("add_channel", add_channel_cmd))
    app.add_handler(CommandHandler("delete_channel", delete_channel_cmd))
    app.add_handler(CommandHandler("choose_channel", choose_channel))
    app.add_handler(CommandHandler("back", back_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_parser), group=1)
