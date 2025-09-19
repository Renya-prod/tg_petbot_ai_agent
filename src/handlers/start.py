# handlers/start.py

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from services import database as db

# ---------------------------
# Вспомогательная функция для клавиатуры
# ---------------------------
def get_channel_keyboard(user_id: int, include_choose=True):
    """
    Возвращает клавиатуру с кнопками выбора и добавления каналов.
    include_choose: показывать ли кнопку '📂 Выбрать канал' если есть каналы
    """
    channels = db.get_channels(user_id)
    keyboard = []

    if include_choose and channels:
        keyboard.append([KeyboardButton("📂 Выбрать канал")])

    keyboard.append([KeyboardButton("➕ Добавить канал")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ---------------------------
# Команда /start
# ---------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Добавляем или обновляем пользователя
    db.add_user(user.id, user.username)
    db_user = db.get_user(user.id)

    keyboard_markup = get_channel_keyboard(db_user["user_id"])
    channels = db.get_channels(db_user["user_id"])

    # Сбрасываем состояние при старте
    context.user_data["state"] = None
    context.user_data["awaiting_channel_name"] = False
    context.user_data["awaiting_channel_selection"] = False

    if not channels:
        await update.message.reply_text(
            f"✅ Пользователь {user.username} добавлен в систему.\n"
            "У вас пока нет каналов. Добавьте канал, чтобы продолжить.",
            reply_markup=keyboard_markup
        )
    else:
        await update.message.reply_text(
            f"Добро пожаловать, {user.username}!\nВыберите канал для работы:",
            reply_markup=keyboard_markup
        )

# ---------------------------
# Универсальный парсер текста
# ---------------------------
async def text_parser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = db.get_user(user.id)
    text = update.message.text.strip()

    # ----------------------------
    # 0. Игнорируем команды /newpost и /addposts и сценарии
    # ----------------------------
    if text.startswith("/newpost") or text.startswith("/addposts") or text.startswith("/done"):
        return  # Пусть CommandHandler или ConversationHandler обрабатывает

    # Если пользователь в сценарии addposts/newpost — не мешаем
    if context.user_data.get("state") in ["addposts", "newpost"]:
        return

    # ----------------------------
    # 1. Добавление канала
    # ----------------------------
    if context.user_data.get("awaiting_channel_name"):
        channel_name = text
        db.add_channel(db_user["user_id"], channel_name)
        context.user_data["awaiting_channel_name"] = False

        reply_markup = get_channel_keyboard(db_user["user_id"])
        await update.message.reply_text(
            f"✅ Канал '{channel_name}' добавлен!\nТеперь можно выбрать канал или добавить ещё один.",
            reply_markup=reply_markup
        )
        return

    # ----------------------------
    # 2. Выбор канала
    # ----------------------------
    if context.user_data.get("awaiting_channel_selection"):
        channel_name = text
        channels = db.get_channels(db_user["user_id"])
        channel = next((ch for ch in channels if ch["name"] == channel_name), None)

        if not channel:
            await update.message.reply_text("❌ Канал не найден, попробуйте снова.")
            return

        context.user_data["selected_channel"] = channel
        context.user_data["awaiting_channel_selection"] = False

        # Показываем команды для работы
        keyboard = [[KeyboardButton("/newpost"), KeyboardButton("/addposts")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            f"✅ Выбран канал '{channel_name}'.\nТеперь можно использовать команды /newpost или /addposts.",
            reply_markup=reply_markup
        )
        return

    # ----------------------------
    # 3. Кнопки "➕ Добавить канал" и "📂 Выбрать канал"
    # ----------------------------
    if text == "➕ Добавить канал":
        await update.message.reply_text("Введите название канала, который хотите добавить:")
        context.user_data["awaiting_channel_name"] = True
        return

    if text == "📂 Выбрать канал":
        channels = db.get_channels(db_user["user_id"])
        if not channels:
            await update.message.reply_text("❗ У вас нет каналов. Сначала добавьте канал через '➕ Добавить канал'.")
            return

        keyboard = [[KeyboardButton(ch["name"])] for ch in channels]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите канал для работы:", reply_markup=reply_markup)
        context.user_data["awaiting_channel_selection"] = True
        return

    # ----------------------------
    # 4. Любой другой текст
    # ----------------------------
    if context.user_data.get("state") not in ["addposts", "newpost"]:
        await update.message.reply_text("❗ Пожалуйста, используйте кнопки или команды для взаимодействия.")

# ---------------------------
# Регистрация хендлеров
# ---------------------------
def setup_start_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_parser), group=1)

