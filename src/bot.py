import logging
from telegram.ext import Application, CommandHandler
from services import database
from config import TELEGRAM_TOKEN

# Handlers
from handlers import start, newpost, addposts


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main():
    # Инициализация базы данных
    database.init_db()

    # Создание приложения
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # ==========================
    # Регистрируем обработчики
    # ==========================

    # Старт и работа с каналами
    start.setup_start_handlers(application)

    # Работа с newpost
    newpost.setup_newpost_handlers(application)

    # Работа с addposts
    addposts.setup_addposts_handlers(application)

    # ==========================
    # Запуск
    # ==========================
    application.run_polling()


if __name__ == "__main__":
    main()
