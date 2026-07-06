import os
import json
import threading
import time
import telebot
from telebot import types
from flask import Flask
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from datetime import datetime

# ================= ЗАГРУЗКА ТОКЕНА (из переменных Render) =================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TELEGRAM_TOKEN:
    raise ValueError("❌ ТОКЕН НЕ НАЙДЕН! Убедитесь, что переменная TELEGRAM_TOKEN добавлена в Environment Variables на Render.")

print(f"✅ Токен загружен из переменных окружения!")

# ================= ИНИЦИАЛИЗАЦИЯ БОТА =================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Файлы для хранения данных
TODO_FILE = "todo_list.json"
HISTORY_FILE = "chat_history.json"

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def load_todo():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_todo(todo_list):
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todo_list, f, ensure_ascii=False, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(history):
    if len(history) > 20:
        history = history[-20:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ================= ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ МОДЕЛИ =================
model = None
tokenizer = None
model_loaded = False

def load_model():
    """Функция для загрузки модели в отдельном потоке"""
    global model, tokenizer, model_loaded
    MODEL_NAME = os.getenv('MODEL_NAME', "ai-forever/rudialogpt-tiny")
    
    print(f"🧠 Фоновый поток: начинаю загрузку модели {MODEL_NAME}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float32,
            low_cpu_mem_usage=True
        )
        model_loaded = True
        print(f"✅ Фоновый поток: модель {MODEL_NAME} успешно загружена!")
    except Exception as e:
        print(f"❌ Фоновый поток: ошибка загрузки модели: {e}")
        model_loaded = False

# ================= ГЕНЕРАЦИЯ ОТВЕТА =================
def generate_response(user_message):
    if not model_loaded:
        return "⏳ Модель еще загружается в фоне. Подождите 1-2 минуты и напишите снова!"
    
    try:
        # ... (весь код генерации остаётся без изменений) ...
        history = load_history()
        context = " ".join(history[-6:]) if history else ""
        prompt = f"{context} Пользователь: {user_message} Ассистент:"
        
        inputs = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=150,
                num_return_sequences=1,
                temperature=0.8,
                top_p=0.9,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
                repetition_penalty=1.2
            )
        
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        if "Ассистент:" in full_response:
            response = full_response.split("Ассистент:")[-1].strip()
        else:
            response = full_response.replace(prompt, "").strip()
        
        if len(response) < 2:
            response = "Я вас слушаю! Расскажите подробнее."
        
        history.append(f"Пользователь: {user_message}")
        history.append(f"Ассистент: {response}")
        save_history(history)
        return response
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        return "😅 Произошла ошибка при генерации ответа."

# ================= ВЕСЬ КОД ОБРАБОТЧИКОВ (без изменений) =================
# ... (сюда вставляются все ваши обработчики команд: start, add, list, done, delete, clear,
# обработчики кнопок, обычных сообщений и бизнес-сообщений) ...
# Я не стал копировать их сюда, чтобы не загромождать, но они должны быть на своих местах.

# ================= ВЕБ-СЕРВЕР ДЛЯ RENDER =================
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    # Возвращаем ответ мгновенно, даже если модель еще не загружена
    return "🤖 Бот запущен и работает!", 200

@flask_app.route('/health')
def health_check_detailed():
    status = "loaded" if model_loaded else "loading"
    return {"status": status, "model": os.getenv('MODEL_NAME', 'unknown')}, 200

# ================= ТОЧКА ВХОДА (ЗАПУСК) =================
if __name__ == '__main__':
    # 1. ЗАПУСКАЕМ веб-сервер в ОСНОВНОМ потоке
    port = int(os.environ.get('PORT', 10000))
    # Запускаем Flask-сервер. Он работает и отвечает на запросы сразу же.
    threading.Thread(target=lambda: flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False), daemon=True).start()
    print(f"🚀 Веб-сервер запущен на порту {port} и отвечает на запросы.")

    # 2. ЗАПУСКАЕМ загрузку модели в отдельном потоке (она не блокирует веб-сервер)
    threading.Thread(target=load_model, daemon=True).start()
    
    # 3. ЗАПУСКАЕМ бота (он работает параллельно с веб-сервером и загрузкой модели)
    print("🤖 Бот запускается...")
    bot.infinity_polling()
