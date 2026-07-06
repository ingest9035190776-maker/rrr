import os
import json
import threading
import random
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import telebot
from telebot import types
from flask import Flask
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

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

# ================= БАЗОВЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ =================
def get_todo_file(chat_id):
    return f"todo_list_{chat_id}.json"

def load_todo(chat_id):
    file_path = get_todo_file(chat_id)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_todo(chat_id, todo_list):
    file_path = get_todo_file(chat_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(todo_list, f, ensure_ascii=False, indent=2)

def get_feeding_file(chat_id):
    return f"feeding_log_{chat_id}.json"

def load_feeding_data(chat_id):
    file_path = get_feeding_file(chat_id)
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_feeding_data(chat_id, data):
    file_path = get_feeding_file(chat_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_today_feeding(chat_id):
    data = load_feeding_data(chat_id)
    today = datetime.now().strftime("%Y-%m-%d")
    return [entry for entry in data if entry.get("date") == today]

def get_today_total_ml(chat_id):
    today_feeding = get_today_feeding(chat_id)
    return sum(entry.get("ml", 0) for entry in today_feeding)

# ================= ИСТОРИЯ ДИАЛОГОВ (общая для всех) =================
HISTORY_FILE = "chat_history.json"

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

# ================= ЗАГРУЗКА МОДЕЛИ =================
model = None
tokenizer = None
model_loaded = False

def load_model():
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

def generate_response(user_message, username=""):
    global model, tokenizer, model_loaded
    if not model_loaded:
        return "⏳ Модель еще загружается. Подождите немного!"
    
    try:
        history = load_history()
        context = " ".join(history[-6:]) if history else ""
        prompt = f"{context} Пользователь: {user_message} Ассистент:"
        inputs = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=256)
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=200,
                num_return_sequences=1,
                temperature=0.9,
                top_p=0.95,
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
            response = random.choice(["Интересно... расскажи еще! 🤔", "Я тебя слушаю! 👂", "Здорово! А что дальше? 😊"])
        history.append(f"Пользователь: {user_message}")
        history.append(f"Ассистент: {response}")
        save_history(history)
        return response
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        return "😅 Ой, я что-то задумался. Давай еще раз?"

# ================= КОМПЛИМЕНТЫ И ШУТКИ =================
COMPLIMENTS = [
    "Ты сегодня просто сияешь! ✨",
    "У тебя прекрасная улыбка! 😊",
    "Ты самый замечательный человек! 💖",
    "Я тобой восхищаюсь! 🌟",
    "Ты делаешь этот мир лучше! 🌍",
]

JOKES = [
    "Почему коты не играют в покер? 🐱 Потому что они всегда блефуют!",
    "Что говорит корова, когда хочет пошутить? 🐄 Му-ха-ха!",
    "Почему рыбы не играют на пианино? 🐟 Потому что они боятся клавиш!",
]

RIDDLES = [
    {"question": "Зимой и летом одним цветом? 🎄", "answer": "елка"},
    {"question": "Что можно увидеть с закрытыми глазами? 😴", "answer": "сон"},
    {"question": "Кто говорит на всех языках? 🗣️", "answer": "эхо"},
]

riddle_mode = {}
current_riddle = {}

# ================= КОМАНДЫ СПИСКА ДЕЛ =================
@bot.message_handler(commands=['add'])
def add_todo(message):
    chat_id = message.chat.id
    text = message.text.replace('/add', '').strip()
    if not text:
        bot.reply_to(message, "❌ Напиши дело после команды.\nПример: /add Купить молоко")
        return
    todo_list = load_todo(chat_id)
    todo_list.append({
        "text": text,
        "done": False,
        "created": datetime.now().strftime("%d.%m.%Y %H:%M")
    })
    save_todo(chat_id, todo_list)
    bot.reply_to(message, f"✅ Добавлено: {text}")

@bot.message_handler(commands=['list'])
def list_todo(message):
    chat_id = message.chat.id
    todo_list = load_todo(chat_id)
    if not todo_list:
        bot.reply_to(message, "📭 Список дел пуст!")
        return
    response = "📋 ТВОЙ СПИСОК ДЕЛ:\n\n"
    for i, item in enumerate(todo_list, 1):
        status = "✅" if item["done"] else "⬜"
        response += f"{i}. {status} {item['text']}\n"
    bot.reply_to(message, response)

@bot.message_handler(commands=['done'])
def done_todo(message):
    chat_id = message.chat.id
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /done <номер>")
            return
        num = int(parts[1])
        todo_list = load_todo(chat_id)
        if 1 <= num <= len(todo_list):
            todo_list[num-1]["done"] = True
            save_todo(chat_id, todo_list)
            bot.reply_to(message, f"✅ Дело '{todo_list[num-1]['text']}' выполнено! 🎉")
        else:
            bot.reply_to(message, f"❌ Дела с номером {num} нет.")
    except ValueError:
        bot.reply_to(message, "❌ Номер должен быть числом.")

@bot.message_handler(commands=['delete'])
def delete_todo(message):
    chat_id = message.chat.id
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Используй: /delete <номер>")
            return
        num = int(parts[1])
        todo_list = load_todo(chat_id)
        if 1 <= num <= len(todo_list):
            deleted = todo_list.pop(num-1)
            save_todo(chat_id, todo_list)
            bot.reply_to(message, f"🗑️ Удалено: {deleted['text']}")
        else:
            bot.reply_to(message, f"❌ Дела с номером {num} нет.")
    except ValueError:
        bot.reply_to(message, "❌ Номер должен быть числом.")

@bot.message_handler(commands=['clear'])
def clear_todo(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Да, очистить", callback_data="clear_todo_yes"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="clear_todo_no"))
    bot.reply_to(message, "⚠️ Удалить все дела?", reply_markup=markup)

# ================= КОРМЛЕНИЯ =================
@bot.message_handler(commands=['feed'])
def add_feeding(message):
    chat_id = message.chat.id
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Укажи объем в мл.\nПример: /feed 120\nМожно с комментарием: /feed 120 отлично поела")
            return
        ml = int(parts[1])
        comment = " ".join(parts[2:]) if len(parts) > 2 else ""
        data = load_feeding_data(chat_id)
        data.append({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": datetime.now().strftime("%H:%M"),
            "ml": ml,
            "comment": comment
        })
        save_feeding_data(chat_id, data)
        bot.reply_to(message, f"✅ Записано кормление: **{ml} мл**\n🕐 {datetime.now().strftime('%H:%M')}{f' ({comment})' if comment else ''}", parse_mode="Markdown")
    except ValueError:
        bot.reply_to(message, "❌ Объем должен быть числом.\nПример: /feed 120")

@bot.message_handler(commands=['feeding'])
def show_feeding(message):
    chat_id = message.chat.id
    today_feeding = get_today_feeding(chat_id)
    if not today_feeding:
        bot.reply_to(message, "🍼 Сегодня кормлений еще не было!\nЧтобы добавить: /feed 120")
        return
    response = "🍼 **ДНЕВНИК КОРМЛЕНИЙ**\n"
    response += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
    for i, entry in enumerate(today_feeding, 1):
        time = entry.get("time", "00:00")
        ml = entry.get("ml", 0)
        comment = entry.get("comment", "")
        response += f"{i}. 🕐 {time} — **{ml} мл**"
        if comment:
            response += f" ({comment})"
        response += "\n"
    total_ml = get_today_total_ml(chat_id)
    response += f"\n📊 **Всего за день: {total_ml} мл**"
    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(commands=['feedstats'])
def feeding_stats(message):
    chat_id = message.chat.id
    data = load_feeding_data(chat_id)
    if not data:
        bot.reply_to(message, "📭 Нет данных о кормлениях.")
        return
    today_feeding = get_today_feeding(chat_id)
    total_ml = get_today_total_ml(chat_id)
    avg_ml = total_ml / len(today_feeding) if today_feeding else 0
    max_ml = max([entry.get("ml", 0) for entry in today_feeding]) if today_feeding else 0
    
    response = "📊 **СТАТИСТИКА КОРМЛЕНИЙ**\n\n"
    response += f"📅 Сегодня: {datetime.now().strftime('%d.%m.%Y')}\n"
    response += f"🍼 Количество: **{len(today_feeding)}**\n"
    response += f"📈 Всего: **{total_ml} мл**\n"
    response += f"📊 Средний объем: **{int(avg_ml)} мл**\n"
    response += f"🔥 Максимум: **{max_ml} мл**\n"
    
    if total_ml > 500:
        response += "\n💪 Отличный аппетит! Дочка молодец! 🌟"
    elif total_ml > 300:
        response += "\n👍 Неплохо! Так держать!"
    else:
        response += "\n😊 Мало, но вкусно! Попробуйте предложить еще позже."
    
    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(commands=['feedchart'])
def feeding_chart(message):
    chat_id = message.chat.id
    data = load_feeding_data(chat_id)
    if not data:
        bot.reply_to(message, "📭 Нет данных для графика.")
        return
    
    # Группируем по дням за последние 7 дней
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    daily_totals = []
    
    for date_str in dates:
        daily_total = sum([entry.get("ml", 0) for entry in data if entry.get("date") == date_str])
        daily_totals.append(daily_total)
    
    # Строим график
    plt.figure(figsize=(10, 5))
    plt.bar(range(len(dates)), daily_totals, color='skyblue', alpha=0.7)
    plt.plot(range(len(dates)), daily_totals, marker='o', color='darkblue', linestyle='-', linewidth=2)
    plt.xticks(range(len(dates)), [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m") for d in dates], rotation=45)
    plt.xlabel('Дата')
    plt.ylabel('Объем (мл)')
    plt.title('Динамика кормлений за последние 7 дней')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    # Добавляем значения над столбцами
    for i, v in enumerate(daily_totals):
        plt.text(i, v + 5, str(v), ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    
    # Сохраняем в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    # Отправляем картинку
    bot.send_photo(message.chat.id, buf, caption="📈 **Динамика кормлений за последние 7 дней**", parse_mode="Markdown")

@bot.message_handler(commands=['clearfeeding'])
def clear_feeding(message):
    chat_id = message.chat.id
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Да, очистить всё", callback_data="clear_feeding_yes"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="clear_feeding_no"))
    bot.reply_to(message, "⚠️ Удалить ВСЕ записи кормлений?", reply_markup=markup)

# ================= ОБРАБОТКА КНОПОК =================
@bot.message_handler(func=lambda message: message.text == "📋 Список дел")
def button_list(message):
    list_todo(message)

@bot.message_handler(func=lambda message: message.text == "➕ Добавить дело")
def button_add(message):
    bot.reply_to(message, "✏️ Напиши /add <текст дела>")

@bot.message_handler(func=lambda message: message.text == "✅ Выполнено")
def button_done(message):
    bot.reply_to(message, "✏️ Напиши /done <номер>")

@bot.message_handler(func=lambda message: message.text == "🍼 Кормления")
def button_feeding(message):
    show_feeding(message)

@bot.message_handler(func=lambda message: message.text == "➕ Записать кормление")
def button_add_feeding(message):
    bot.reply_to(message, "✏️ Напиши объем в мл:\n/feed 120\n\nМожно добавить комментарий:\n/feed 120 отлично поела")

@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def button_stats(message):
    feeding_stats(message)

@bot.message_handler(func=lambda message: message.text == "📈 График")
def button_chart(message):
    feeding_chart(message)

@bot.message_handler(func=lambda message: message.text == "🗑️ Очистить кормления")
def button_clear_feeding(message):
    clear_feeding(message)

@bot.message_handler(func=lambda message: message.text == "💝 Комплимент")
def button_compliment(message):
    bot.reply_to(message, random.choice(COMPLIMENTS))

@bot.message_handler(func=lambda message: message.text == "😂 Шутка")
def button_joke(message):
    bot.reply_to(message, random.choice(JOKES))

@bot.message_handler(func=lambda message: message.text == "🧩 Загадка")
def button_riddle(message):
    chat_id = message.chat.id
    riddle = random.choice(RIDDLES)
    riddle_mode[chat_id] = True
    current_riddle[chat_id] = riddle
    bot.reply_to(message, f"❓ Загадка: {riddle['question']}\n\nОтправь свой ответ!")

# ================= CALLBACK-ОБРАБОТЧИКИ =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    
    if call.data == "clear_todo_yes":
        save_todo(chat_id, [])
        bot.answer_callback_query(call.id, "✅ Список дел очищен!")
        bot.edit_message_text("🗑️ Список дел очищен!", chat_id, call.message.message_id)
    elif call.data == "clear_todo_no":
        bot.answer_callback_query(call.id, "❌ Отменено")
        bot.edit_message_text("✅ Очистка отменена", chat_id, call.message.message_id)
    elif call.data == "clear_feeding_yes":
        save_feeding_data(chat_id, [])
        bot.answer_callback_query(call.id, "✅ Все записи кормлений очищены!")
        bot.edit_message_text("🗑️ Все записи кормлений удалены!", chat_id, call.message.message_id)
    elif call.data == "clear_feeding_no":
        bot.answer_callback_query(call.id, "❌ Отменено")
        bot.edit_message_text("✅ Очистка отменена", chat_id, call.message.message_id)

# ================= ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ =================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    
    # Проверяем, не отгадываем ли загадку
    if riddle_mode.get(chat_id, False):
        riddle = current_riddle.get(chat_id)
        if riddle and message.text.lower().strip() == riddle["answer"].lower():
            riddle_mode[chat_id] = False
            current_riddle[chat_id] = None
            bot.reply_to(message, f"🎉 Правильно! Ты супер-умный! 💪")
            return
        elif riddle:
            bot.reply_to(message, f"🤔 Не угадал! Попробуй еще раз.\nПодсказка: слово начинается на букву '{riddle['answer'][0].upper()}'")
            return
    
    # Обработка специальных команд в сообщениях
    if message.text.lower() == "комплимент" or message.text.lower() == "похвали":
        bot.reply_to(message, random.choice(COMPLIMENTS))
        return
    elif message.text.lower() == "шутка" or message.text.lower() == "смеш":
        bot.reply_to(message, random.choice(JOKES))
        return
    elif message.text.lower() == "загадка":
        riddle = random.choice(RIDDLES)
        riddle_mode[chat_id] = True
        current_riddle[chat_id] = riddle
        bot.reply_to(message, f"❓ Загадка: {riddle['question']}\n\nОтправь свой ответ!")
        return
    elif message.text.lower() == "помощь" or message.text.lower() == "help":
        bot.reply_to(message, 
                     "📚 **Команды и кнопки:**\n\n"
                     "📋 **Список дел:**\n"
                     "/add <текст> - добавить дело\n"
                     "/list - показать список\n"
                     "/done <номер> - отметить выполненным\n"
                     "/delete <номер> - удалить дело\n"
                     "/clear - очистить список\n\n"
                     "🍼 **Кормления:**\n"
                     "/feed <мл> - записать кормление\n"
                     "/feeding - показать кормления за сегодня\n"
                     "/feedstats - статистика за день\n"
                     "/feedchart - график за 7 дней\n"
                     "/clearfeeding - очистить все записи\n\n"
                     "🎮 **Развлечения:**\n"
                     "Напиши: комплимент, шутка, загадка", parse_mode="Markdown")
        return
    
    # Генерация ответа через модель
    username = message.from_user.first_name or ""
    bot.send_chat_action(message.chat.id, 'typing')
    reply = generate_response(message.text, username)
    bot.reply_to(message, reply)

# ================= БИЗНЕС-СООБЩЕНИЯ =================
@bot.business_message_handler(func=lambda message: True)
def handle_business_message(message):
    if not message.text:
        return
    username = message.from_user.first_name or ""
    bot.send_chat_action(message.chat.id, 'typing')
    reply = generate_response(message.text, username)
    bot.reply_to(message, f"🏢 {reply}")

@bot.business_connection_handler()
def handle_business_connection(connection):
    print(f"✅ Бизнес-аккаунт подключен: {connection.user_id}")

# ================= КОМАНДА START =================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    btn1 = types.KeyboardButton("📋 Список дел")
    btn2 = types.KeyboardButton("➕ Добавить дело")
    btn3 = types.KeyboardButton("✅ Выполнено")
    btn4 = types.KeyboardButton("🍼 Кормления")
    btn5 = types.KeyboardButton("➕ Записать кормление")
    btn6 = types.KeyboardButton("📊 Статистика")
    btn7 = types.KeyboardButton("📈 График")
    btn8 = types.KeyboardButton("🗑️ Очистить кормления")
    btn9 = types.KeyboardButton("💝 Комплимент")
    btn10 = types.KeyboardButton("😂 Шутка")
    btn11 = types.KeyboardButton("🧩 Загадка")
    btn12 = types.KeyboardButton("📚 Помощь")
    markup.add(btn1, btn2, btn3)
    markup.add(btn4, btn5, btn6)
    markup.add(btn7, btn8)
    markup.add(btn9, btn10, btn11)
    markup.add(btn12)
    
    bot.reply_to(message, 
        "👋 Привет! Я семейный помощник!\n\n"
        "🍼 Дневник кормлений дочки\n"
        "📋 Общий список дел\n"
        "🎮 Игры и развлечения\n\n"
        "Используй кнопки ниже или вводи команды!",
        reply_markup=markup)

# ================= ВЕБ-СЕРВЕР ДЛЯ RENDER =================
flask_app = Flask(__name__)

@flask_app.route('/')
def health_check():
    return "🤖 Бот работает!", 200

# ================= ЗАПУСК =================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    ).start()
    print(f"🚀 Веб-сервер запущен на порту {port}")
    
    threading.Thread(target=load_model, daemon=True).start()
    print("📥 Модель загружается в фоне...")
    
    print("🤖 Бот запускается...")
    bot.infinity_polling()
