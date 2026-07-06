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

# ================= ЗАГРУЗКА ТОКЕНА =================
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

if not TELEGRAM_TOKEN:
    try:
        from config import TELEGRAM_TOKEN as CONFIG_TOKEN
        TELEGRAM_TOKEN = CONFIG_TOKEN
    except ImportError:
        pass

if not TELEGRAM_TOKEN:
    raise ValueError("❌ ТОКЕН НЕ НАЙДЕН!")

print(f"✅ Токен загружен!")

# ================= ИНИЦИАЛИЗАЦИЯ БОТА =================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Файлы для хранения данных
TODO_FILE = "todo_list.json"
HISTORY_FILE = "chat_history.json"

# ================= РАБОТА СО СПИСКОМ ДЕЛ =================
def load_todo():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_todo(todo_list):
    with open(TODO_FILE, "w", encoding="utf-8") as f:
        json.dump(todo_list, f, ensure_ascii=False, indent=2)

# ================= РАБОТА С ИСТОРИЕЙ =================
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

# ================= ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДЛЯ МОДЕЛИ =================
model = None
tokenizer = None
model_loaded = False

def load_model():
    """Загружает модель в фоновом потоке"""
    global model, tokenizer, model_loaded
    
    MODEL_NAME = os.getenv('MODEL_NAME', "ai-forever/rudialogpt-tiny")
    print(f"📥 Начинаю загрузку модели {MODEL_NAME} в фоновом режиме...")
    
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
        print(f"✅ Модель {MODEL_NAME} успешно загружена!")
    except Exception as e:
        print(f"❌ Ошибка загрузки модели: {e}")
        model_loaded = False

def generate_response(user_message):
    """Генерирует ответ, если модель загружена"""
    global model, tokenizer, model_loaded
    
    if not model_loaded:
        return "⏳ Модель еще загружается. Подождите немного и попробуйте снова!"
    
    try:
        history = load_history()
        context = " ".join(history[-6:]) if history else ""
        
        prompt = f"{context} Пользователь: {user_message} Ассистент:"
        
        inputs = tokenizer.encode(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=256
        )
        
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

# ================= ОБРАБОТЧИКИ КОМАНД (без изменений) =================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("📋 Список дел")
    btn2 = types.KeyboardButton("➕ Добавить дело")
    btn3 = types.KeyboardButton("✅ Выполнено")
    btn4 = types.KeyboardButton("🗑️ Очистить всё")
    markup.add(btn1, btn2, btn3, btn4)
    
    bot.reply_to(message, 
        "👋 Привет! Я твой личный ИИ-ассистент.\n\n"
        "📝 Что я умею:\n"
        "/add <текст> - добавить дело\n"
        "/list - показать список дел\n"
        "/done <номер> - отметить дело выполненным\n"
        "/delete <номер> - удалить дело\n"
        "/clear - очистить весь список\n\n"
        "🤖 Модель загружается в фоновом режиме. Подождите 1-2 минуты!",
        reply_markup=markup
    )

@bot.message_handler(commands=['add'])
def add_todo(message):
    text = message.text.replace('/add', '').strip()
    if not text:
        bot.reply_to(message, "❌ Напиши дело после команды.\nПример: /add Купить молоко")
        return
    
    todo_list = load_todo()
    todo_list.append({
        "text": text,
        "done": False,
        "created": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    save_todo(todo_list)
    bot.reply_to(message, f"✅ Добавлено: {text}")

@bot.message_handler(commands=['list'])
def list_todo(message):
    todo_list = load_todo()
    if not todo_list:
        bot.reply_to(message, "📭 Список дел пуст! Добавь что-нибудь через /add")
        return
    
    response = "📋 ТВОЙ СПИСОК ДЕЛ:\n\n"
    for i, item in enumerate(todo_list, 1):
        status = "✅" if item["done"] else "⬜"
        response += f"{i}. {status} {item['text']}\n"
        if not item["done"]:
            response += f"   ⏳ Добавлено: {item['created']}\n"
    
    bot.reply_to(message, response)

@bot.message_handler(commands=['done'])
def done_todo(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /done <номер>")
            return
        num = int(parts[1])
        todo_list = load_todo()
        if 1 <= num <= len(todo_list):
            todo_list[num-1]["done"] = True
            save_todo(todo_list)
            bot.reply_to(message, f"✅ Дело '{todo_list[num-1]['text']}' выполнено! 🎉")
        else:
            bot.reply_to(message, f"❌ Дела с номером {num} нет. Всего дел: {len(todo_list)}")
    except ValueError:
        bot.reply_to(message, "❌ Номер должен быть числом. Пример: /done 3")

@bot.message_handler(commands=['delete'])
def delete_todo(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /delete <номер>")
            return
        num = int(parts[1])
        todo_list = load_todo()
        if 1 <= num <= len(todo_list):
            deleted = todo_list.pop(num-1)
            save_todo(todo_list)
            bot.reply_to(message, f"🗑️ Удалено: {deleted['text']}")
        else:
            bot.reply_to(message, f"❌ Дела с номером {num} нет")
    except ValueError:
        bot.reply_to(message, "❌ Номер должен быть числом")

@bot.message_handler(commands=['clear'])
def clear_todo(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Да, очистить", callback_data="clear_yes"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="clear_no"))
    bot.reply_to(message, "⚠️ Вы уверены, что хотите удалить ВСЕ дела?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("clear_"))
def callback_clear(call):
    if call.data == "clear_yes":
        save_todo([])
        bot.answer_callback_query(call.id, "✅ Список очищен!")
        bot.edit_message_text("🗑️ Список дел очищен!", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Отменено")
        bot.edit_message_text("✅ Очистка отменена", call.message.chat.id, call.message.message_id)

# ================= ОБРАБОТКА КНОПОК =================
@bot.message_handler(func=lambda message: message.text == "📋 Список дел")
def button_list(message):
    list_todo(message)

@bot.message_handler(func=lambda message: message.text == "➕ Добавить дело")
def button_add(message):
    bot.reply_to(message, "✏️ Напиши /add <текст дела>\nПример: /add Купить продукты")

@bot.message_handler(func=lambda message: message.text == "✅ Выполнено")
def button_done(message):
    bot.reply_to(message, "✏️ Напиши /done <номер>\nПример: /done 3")

@bot.message_handler(func=lambda message: message.text == "🗑️ Очистить всё")
def button_clear(message):
    clear_todo(message)

# ================= ОБЫЧНЫЕ СООБЩЕНИЯ =================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text.startswith('/'):
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    reply = generate_response(message.text)
    bot.reply_to(message, reply)

# ================= БИЗНЕС-СООБЩЕНИЯ =================
@bot.business_message_handler(func=lambda message: True)
def handle_business_message(message):
    if not message.text:
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    reply = generate_response(message.text)
    bot.reply_to(message, f"🏢 {reply}")

@bot.business_connection_handler()
def handle_business_connection(connection):
    print(f"✅ Бизнес-аккаунт подключен: {connection.user_id}")

# ================= ВЕБ-СЕРВЕР ДЛЯ RENDER =================
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "🤖 Бот работает!", 200

@flask_app.route('/health')
def health_check_detailed():
    status = "loaded" if model_loaded else "loading"
    return {"status": status, "model": os.getenv('MODEL_NAME', 'unknown')}, 200

# ================= ЗАПУСК =================
if __name__ == '__main__':
    # 1. СНАЧАЛА запускаем веб-сервер, чтобы Render увидел порт
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    ).start()
    print(f"🚀 Веб-сервер запущен на порту {port}")
    
    # 2. ПОТОМ запускаем загрузку модели в отдельном потоке
    threading.Thread(target=load_model, daemon=True).start()
    print("📥 Модель начинает загружаться в фоне...")
    
    # 3. ЗАПУСКАЕМ бота
    print("🤖 Бот запускается...")
    bot.infinity_polling()
