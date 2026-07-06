import os
import threading
from flask import Flask
import telebot
from config import Config
from storage import Database
from ai import AIModel
from handlers import Handlers

# Инициализация базы данных
db = Database(Config.DATABASE_PATH)

# Инициализация ИИ-модели
ai = AIModel(Config.MODEL_NAME)

# Инициализация бота
bot = telebot.TeleBot(Config.TELEGRAM_TOKEN)

# Регистрация обработчиков
handlers = Handlers(bot, db, ai)

# Веб-сервер для Render
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "🤖 Бот работает!", 200

@flask_app.route('/health')
def health_check_detailed():
    return {"status": "ok", "model": Config.MODEL_NAME}, 200

if __name__ == '__main__':
    # Запускаем веб-сервер для Render
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    ).start()
    print(f"🚀 Веб-сервер запущен на порту {port}")
    
    print("🤖 Бот запускается...")
    bot.infinity_polling()