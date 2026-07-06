import os
import json
import torch
import telebot
from telebot import types
from transformers import AutoModelForCausalLM, AutoTokenizer
from datetime import datetime

# ================= ЗАГРУЗКА ТОКЕНА =================
# Пробуем загрузить из .env (если установлен python-dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Если dotenv не установлен - просто игнорируем

# Пробуем получить токен из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Если не нашли - пробуем загрузить из config.py
if not TELEGRAM_TOKEN:
    try:
        from config import TELEGRAM_TOKEN as CONFIG_TOKEN
        TELEGRAM_TOKEN = CONFIG_TOKEN
    except ImportError:
        pass

# Если всё еще нет токена - ошибка
if not TELEGRAM_TOKEN:
    raise ValueError("""
    ❌ ТОКЕН НЕ НАЙДЕН!
    
    Создайте один из файлов:
    1. .env с содержимым: TELEGRAM_TOKEN=ваш_токен
    2. config.py с содержимым: TELEGRAM_TOKEN = "ваш_токен"
    
    Или установите переменную окружения TELEGRAM_TOKEN
    """)

print(f"✅ Токен загружен! Начинается: {TELEGRAM_TOKEN[:10]}...")

# ================= ОСТАЛЬНОЙ КОД =================
# Загрузка модели
MODEL_NAME = os.getenv('MODEL_NAME', "sberbank-ai/rugpt3small_based_on_gpt2")

print(f"📥 Загрузка модели {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("✅ Модель загружена!")

# Инициализация бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Пути к файлам
TODO_FILE = "todo_list.json"
HISTORY_FILE = "chat_history.json"

# ... (весь остальной код из предыдущего сообщения)
# Обработчики команд и сообщений

if __name__ == "__main__":
    print("🤖 Бот запущен!")
    bot.infinity_polling()
