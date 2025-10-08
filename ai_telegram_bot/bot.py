import logging
from telegram.ext import Application
from services import database
from config import TELEGRAM_TOKEN, WEBHOOK_URL
from handlers import start, newpost, addposts

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

def main():
    database.init_db()

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    start.setup_start_handlers(application)
    newpost.setup_newpost_handlers(application)
    addposts.setup_addposts_handlers(application)

    application.run_webhook(
        listen="0.0.0.0",
        port=8443,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}",
    )

if __name__ == "__main__":
    main()
