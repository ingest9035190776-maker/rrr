import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

class Config:
    # Токен бота
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN не найден в .env!")
    
    # Настройки модели
    MODEL_NAME = os.getenv('MODEL_NAME', 'ai-forever/rudialogpt-tiny')
    
    # Пути к файлам
    DATABASE_PATH = 'family.db'
    
    # Настройки бота
    BOT_NAME = "Семейный Помощник"  # Имя бота
    BOT_EMOJI = "👨‍👩‍👧‍👦"
    
    # Режимы общения
    MODES = {
        "family": {
            "name": "Семейный",
            "emoji": "💕",
            "style": "заботливый и теплый",
            "greeting": "Привет, моя хорошая! Как у вас дела? 🥰"
        },
        "funny": {
            "name": "Веселый",
            "emoji": "🤪",
            "style": "игривый и смешной",
            "greeting": "Ооо, кто тут! Готов к приключениям? 🚀"
        },
        "strict": {
            "name": "Деловой",
            "emoji": "📌",
            "style": "четкий и по делу",
            "greeting": "Здравствуйте. Чем могу помочь?"
        },
        "child": {
            "name": "Детский",
            "emoji": "🌈",
            "style": "дружелюбный и игривый",
            "greeting": "Приветик! Поиграем? 🎮"
        }
    }