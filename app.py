import os
import json
import threading
import random
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
FAMILY_FILE = "family_data.json"

# ================= РАБОТА С ДАННЫМИ =================
def load_json(file_path, default=None):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_todo():
    return load_json(TODO_FILE, [])

def save_todo(todo_list):
    save_json(TODO_FILE, todo_list)

def load_history():
    return load_json(HISTORY_FILE, [])

def save_history(history):
    if len(history) > 20:
        history = history[-20:]
    save_json(HISTORY_FILE, history)

def load_family_data():
    return load_json(FAMILY_FILE, {"mood": "neutral", "mode": "family"})

def save_family_data(data):
    save_json(FAMILY_FILE, data)

# ================= СЕМЕЙНЫЕ НАСТРОЙКИ =================
family_data = load_family_data()

# Режимы общения
MODES = {
    "family": {
        "name": "👨‍👩‍👧‍👦 Семейный",
        "emoji": "💕",
        "style": "заботливый и теплый",
        "greeting": "Привет, моя хорошая! Как у тебя дела? 🥰"
    },
    "funny": {
        "name": "😂 Веселый",
        "emoji": "🤪",
        "style": "игривый и смешной",
        "greeting": "Ооо, кто тут! Готов к приключениям? 🚀"
    },
    "strict": {
        "name": "📋 Деловой",
        "emoji": "📌",
        "style": "четкий и по делу",
        "greeting": "Здравствуйте. Чем могу помочь?"
    },
    "child": {
        "name": "🧒 Детский",
        "emoji": "🌈",
        "style": "дружелюбный и игривый",
        "greeting": "Приветик! Поиграем? 🎮"
    }
}

# ================= ГЕНЕРАЦИЯ ОТВЕТОВ =================
def get_mode_style():
    mode = family_data.get("mode", "family")
    return MODES.get(mode, MODES["family"])

# Шутки и комплименты
JOKES = [
    "Почему коты не играют в покер? 🐱 Потому что они всегда блефуют!",
    "Что говорит корова, когда хочет пошутить? 🐄 Му-ха-ха!",
    "Почему рыбы не играют на пианино? 🐟 Потому что они боятся клавиш!",
    "Как называется медведь без ушей? 🐻 М-м-м...",
]

COMPLIMENTS = [
    "Ты сегодня просто сияешь! ✨",
    "У тебя прекрасная улыбка! 😊",
    "Ты самый замечательный человек! 💖",
    "Я тобой восхищаюсь! 🌟",
    "Ты делаешь этот мир лучше! 🌍",
]

CHILD_PRAISE = [
    "Ты такой умный! 🌟",
    "Как здорово у тебя получается! 🎉",
    "Ты просто супергерой! 🦸‍♂️",
    "Я горжусь тобой! 💪",
]

RIDDLES = [
    {"question": "Зимой и летом одним цветом? 🎄", "answer": "елка"},
    {"question": "Что можно увидеть с закрытыми глазами? 😴", "answer": "сон"},
    {"question": "Кто говорит на всех языках? 🗣️", "answer": "эхо"},
]

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
    """Генерирует ответ с учетом режима общения"""
    global model, tokenizer, model_loaded
    
    # Проверяем, не играем ли мы в загадки
    if family_data.get("riddle_mode"):
        return check_riddle_answer(user_message)
    
    # Проверяем специальные команды
    if "комплимент" in user_message.lower() or "похвали" in user_message.lower():
        return random.choice(COMPLIMENTS)
    
    if "шутка" in user_message.lower() or "смеш" in user_message.lower():
        return random.choice(JOKES)
    
    if "загадка" in user_message.lower():
        return start_riddle()
    
    if "помощь" in user_message.lower() or "help" in user_message.lower():
        return get_help_message()
    
    # Если модель не загружена
    if not model_loaded:
        return "⏳ Я еще учусь. Подожди немного, чтобы я стал умнее! 🧠"
    
    # Генерация с учетом режима
    mode_style = get_mode_style()
    mode_name = mode_style["name"]
    
    try:
        history = load_history()
        context = " ".join(history[-6:]) if history else ""
        
        # Добавляем контекст в зависимости от режима
        style_prompt = f"Ты {mode_style['style']} ассистент. Отвечай в {mode_style['style']} тоне."
        
        if username:
            style_prompt += f" Обращайся к пользователю по имени {username}."
        
        prompt = f"{style_prompt} Контекст: {context} Пользователь: {user_message} Ассистент:"
        
        inputs = tokenizer.encode(
            prompt, 
            return_tensors="pt", 
            truncation=True, 
            max_length=256
        )
        
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
            response = random.choice([
                "Интересно... расскажи еще! 🤔",
                "Я тебя слушаю! 👂",
                "Здорово! А что дальше? 😊"
            ])
        
        # Добавляем эмодзи в зависимости от режима
        if mode_name in response:
            pass
        else:
            response = f"{mode_style['emoji']} {response}"
        
        history.append(f"Пользователь: {user_message}")
        history.append(f"Ассистент: {response}")
        save_history(history)
        
        return response
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        return "😅 Ой, я что-то задумался. Давай еще раз?"

# ================= ЗАГАДКИ И ИГРЫ =================
def start_riddle():
    riddle = random.choice(RIDDLES)
    family_data["riddle_mode"] = True
    family_data["current_riddle"] = riddle
    save_family_data(family_data)
    return f"❓ Загадка: {riddle['question']}\n\nОтправь свой ответ!"

def check_riddle_answer(user_message):
    riddle = family_data.get("current_riddle")
    if not riddle:
        family_data["riddle_mode"] = False
        save_family_data(family_data)
        return "🎮 Загадки закончились! Хочешь еще?"
    
    if user_message.lower().strip() == riddle["answer"].lower():
        family_data["riddle_mode"] = False
        family_data["current_riddle"] = None
        save_family_data(family_data)
        return f"🎉 Правильно! Ты супер-умный! 💪\n\nХочешь еще загадку? Напиши 'загадка'!"
    else:
        return f"🤔 Не угадал! Попробуй еще раз.\nПодсказка: это слово начинается на букву '{riddle['answer'][0].upper()}'"

def get_help_message():
    return """
📚 **Я умею много полезного:**

🎭 **Режимы общения:**
/start - начать заново
/mode family - 👨‍👩‍👧‍👦 Семейный режим
/mode funny - 😂 Веселый режим
/mode strict - 📋 Деловой режим
/mode child - 🧒 Детский режим

🎮 **Игры и развлечения:**
"комплимент" - получить комплимент 💝
"шутка" - послушать шутку 😂
"загадка" - отгадать загадку 🧩

📝 **Список дел:**
/add <текст> - добавить дело
/list - посмотреть список
/done <номер> - отметить выполненным
/delete <номер> - удалить дело

💬 **Просто пиши мне**, и я отвечу как друг и помощник! 
"""

# ================= ОБРАБОТЧИКИ КОМАНД =================
@bot.message_handler(commands=['start', 'help'])
def start(message):
    mode_style = get_mode_style()
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    btn1 = types.KeyboardButton("📋 Список дел")
    btn2 = types.KeyboardButton("➕ Добавить дело")
    btn3 = types.KeyboardButton("✅ Выполнено")
    btn4 = types.KeyboardButton("🎭 Сменить режим")
    btn5 = types.KeyboardButton("🎮 Поиграем")
    btn6 = types.KeyboardButton("💝 Комплимент")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    
    # Получаем имя пользователя
    username = message.from_user.first_name or "друг"
    
    # Случайное приветствие
    greetings = [
        f"👋 Привет, {username}! {mode_style['greeting']}",
        f"🌟 Здравствуй, {username}! Рад(а) тебя видеть!",
        f"💫 Приветик, {username}! Как настроение?",
    ]
    
    bot.reply_to(message, 
        f"{random.choice(greetings)}\n\n"
        f"🎭 Текущий режим: {mode_style['name']}\n\n"
        f"📌 Напиши 'помощь' или 'help' чтобы увидеть все команды.",
        reply_markup=markup
    )

@bot.message_handler(commands=['mode'])
def change_mode(message):
    args = message.text.split()
    if len(args) < 2:
        modes_list = "\n".join([f"/mode {key} - {value['name']}" for key, value in MODES.items()])
        bot.reply_to(message, f"🎭 Выбери режим:\n\n{modes_list}")
        return
    
    mode_key = args[1]
    if mode_key in MODES:
        family_data["mode"] = mode_key
        save_family_data(family_data)
        mode = MODES[mode_key]
        bot.reply_to(message, 
            f"✅ Режим изменен на {mode['name']}!\n"
            f"{mode['emoji']} Теперь я буду {mode['style']}."
        )
    else:
        bot.reply_to(message, f"❌ Режим '{mode_key}' не найден.\nДоступные: {', '.join(MODES.keys())}")

# ================= ОБЫЧНЫЕ ОБРАБОТЧИКИ ДЕЛ =================
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
    bot.reply_to(message, f"✅ Добавлено: {text}\n\n{random.choice(COMPLIMENTS)}")

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
            bot.reply_to(message, f"✅ Дело '{todo_list[num-1]['text']}' выполнено! 🎉\n\n{random.choice(COMPLIMENTS)}")
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

@bot.message_handler(func=lambda message: message.text == "🎭 Сменить режим")
def button_mode(message):
    modes_list = "\n".join([f"/mode {key} - {value['name']}" for key, value in MODES.items()])
    bot.reply_to(message, f"🎭 Выбери режим:\n\n{modes_list}")

@bot.message_handler(func=lambda message: message.text == "🎮 Поиграем")
def button_game(message):
    games = [
        "🎯 Хочешь загадку? Напиши 'загадка'!",
        "😄 Послушай шутку! Напиши 'шутка'!",
        "💝 Получи комплимент! Напиши 'комплимент'!",
    ]
    bot.reply_to(message, random.choice(games))

@bot.message_handler(func=lambda message: message.text == "💝 Комплимент")
def button_compliment(message):
    bot.reply_to(message, random.choice(COMPLIMENTS))

# ================= ОБЫЧНЫЕ СООБЩЕНИЯ =================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text.startswith('/'):
        return
    
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

# ================= ВЕБ-СЕРВЕР =================
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
    port = int(os.environ.get('PORT', 10000))
    threading.Thread(
        target=lambda: flask_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
    ).start()
    print(f"🚀 Веб-сервер запущен на порту {port}")
    
    threading.Thread(target=load_model, daemon=True).start()
    print("📥 Модель начинает загружаться в фоне...")
    
    print("🤖 Бот запускается...")
    bot.infinity_polling()
