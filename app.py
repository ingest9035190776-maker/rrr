import os
import json
import threading
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
    raise ValueError("""
    ❌ ТОКЕН НЕ НАЙДЕН!
    Создайте файл .env с TELEGRAM_TOKEN=ваш_токен
    """)

print(f"✅ Токен загружен!")

# ================= ЛЕГКОВЕСНАЯ МОДЕЛЬ =================
# Используем tiny-модель для экономии памяти (~100 МБ)
MODEL_NAME = "cointegrated/ru-gpt-tiny"

print(f"📥 Загрузка легковесной модели {MODEL_NAME}...")

# Загружаем токенизатор
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# Устанавливаем pad_token, если его нет
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Загружаем модель в режиме CPU (экономит память)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32,  # Используем float32 для стабильности
    low_cpu_mem_usage=True       # Оптимизация памяти
)

print("✅ Модель загружена!")

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

# ================= ГЕНЕРАЦИЯ ОТВЕТА =================
def generate_response(user_message):
    """Генерирует ответ с помощью легковесной модели"""
    
    history = load_history()
    context = " ".join(history[-6:]) if history else ""
    
    # Формируем промпт
    prompt = f"{context} Пользователь: {user_message} Ассистент:"
    
    # Токенизируем
    inputs = tokenizer.encode(
        prompt, 
        return_tensors="pt", 
        truncation=True, 
        max_length=256  # Уменьшаем для экономии памяти
    )
    
    # Генерируем ответ
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
    
    # Декодируем
    full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Извлекаем ответ ассистента
    if "Ассистент:" in full_response:
        response = full_response.split("Ассистент:")[-1].strip()
    else:
        response = full_response.replace(prompt, "").strip()
    
    if len(response) < 2:
        response = "Я вас слушаю! Расскажите подробнее."
    
    # Сохраняем в историю
    history.append(f"Пользователь: {user_message}")
    history.append(f"Ассистент: {response}")
    save_history(history)
    
    return response

# ================= ОБРАБОТЧИКИ КОМАНД =================
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
        "🤖 Я отвечаю с помощью легковесной ИИ-модели!",
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
    
    try:
        reply = generate_response(message.text)
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        reply = "😅 Извини, я немного устал. Давай еще раз?"
    
    bot.reply_to(message, reply)

# ================= БИЗНЕС-СООБЩЕНИЯ =================
@bot.business_message_handler(func=lambda message: True)
def handle_business_message(message):
    """Обработка сообщений из бизнес-аккаунта"""
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        reply = generate_response(message.text)
    except Exception as e:
        print(f"Ошибка генерации бизнес-сообщения: {e}")
        reply = "😅 Извини, я немного устал. Давай еще раз?"
    
    bot.reply_to(message, f"🏢 {reply}")

@bot.business_connection_handler()
def handle_business_connection(connection):
    """Обработчик подключения бизнес-аккаунта"""
    print(f"✅ Бизнес-аккаунт подключен: {connection.user_id}")

# ================= ВЕБ-СЕРВЕР ДЛЯ RENDER =================
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "🤖 Бот работает!", 200

@flask_app.route('/health')
def health_check_detailed():
    return {"status": "ok", "model": MODEL_NAME}, 200

# ================= ЗАПУСК =================
if __name__ == '__main__':
    # Запускаем веб-сервер для Render
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    ).start()
    
    print(f"🚀 Бот запущен на порту {port}")
    print(f"🧠 Модель: {MODEL_NAME}")
    print("📋 Бот готов к работе!")
    
    # Запускаем бота
    bot.infinity_polling()
