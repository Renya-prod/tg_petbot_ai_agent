# 🤖 AI Telegram Bot

Telegram-бот для генерации и публикации постов в каналы с помощью LLM.  

---

## 🚀 Установка b pfgecr

1. Клонируйте репозиторий:
git clone https://github.com/username/ai-telegram-bot.git
cd ai-telegram-bot

2. Создайте виртуальное окружение в папке:
python3 -m venv env
source env/bin/activate   # для Linux/Mac

3. Скачайте баблиотеки:
pip install -r requirements.txt # если потребуется в консоле установить что-то дополнительно, установите

4. Вставьте все нужные токены в конфиг:
TELEGRAM_TOKEN=your-telegram-bot-token # получить через BotFather в телеграмм
GIGACHAT_TOKEN=your-gigachat-api-key # можно получить прочитав документацию на сайте
DATABASE_URL=postgresql:user:password # создать локально бд через postgres

5. Запускайте bot.py
