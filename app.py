import telebot
from telebot import types
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import json
import os
from datetime import datetime

# ================= НАСТРОЙКИ =================
TELEGRAM_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"  # ВСТАВЬТЕ СВОЙ ТОКЕН

# Модель (используем облегчённую русскую модель)
MODEL_NAME = "sberbank-ai/rugpt3small_based_on_gpt2"  # 300MB
# Альтернативы (если мощный ПК):
# MODEL_NAME = "sberbank-ai/rugpt3medium_based_on_gpt2"  # 1.5GB
# MODEL_NAME = "microsoft/DialoGPT-medium"  # для английского

# Файлы для хранения
TODO_FILE = "todo_list.json"
HISTORY_FILE = "chat_history.json"

# ================= ЗАГРУЗКА МОДЕЛИ =================
print(f"📥 Загрузка модели {MODEL_NAME}... Это может занять 2-5 минут при первом запуске.")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

# Если модель не имеет pad_token, устанавливаем
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

print("✅ Модель загружена!")

# ================= ИНИЦИАЛИЗАЦИЯ БОТА =================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

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
    # Оставляем только последние 20 сообщений (10 диалогов)
    if len(history) > 20:
        history = history[-20:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# ================= ГЕНЕРАЦИЯ ОТВЕТА =================
def generate_response(user_message):
    """Генерирует ответ с помощью локальной модели"""
    
    # Загружаем историю
    history = load_history()
    
    # Формируем контекст (последние 6 сообщений)
    context = " ".join(history[-6:]) if history else ""
    
    # Формируем промпт
    prompt = f"{context} Пользователь: {user_message} Ассистент:"
    
    # Токенизируем
    inputs = tokenizer.encode(prompt, return_tensors="pt", truncation=True, max_length=512)
    
    # Генерируем ответ
    with torch.no_grad():
        outputs = model.generate(
            inputs,
            max_length=150,
            num_return_sequences=1,
            temperature=0.8,  # Креативность (0.2 - сухой, 1.0 - креативный)
            top_p=0.9,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.2  # Чтобы не повторялся
        )
    
    # Декодируем
    full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Извлекаем только ответ ассистента
    if "Ассистент:" in full_response:
        response = full_response.split("Ассистент:")[-1].strip()
    else:
        response = full_response.replace(prompt, "").strip()
    
    # Если ответ пустой или слишком короткий
    if len(response) < 2:
        response = "Я вас слушаю! Расскажите подробнее."
    
    # Сохраняем в историю
    history.append(f"Пользователь: {user_message}")
    history.append(f"Ассистент: {response}")
    save_history(history)
    
    return response

# ================= КОМАНДЫ БОТА =================
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
        "/clear - очистить весь список\n"
        "/history - показать историю диалога\n\n"
        "🤖 Я отвечаю с помощью ИИ и запоминаю контекст разговора!",
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
    save_todo([])
    bot.reply_to(message, "🗑️ Весь список дел очищен!")

@bot.message_handler(commands=['history'])
def show_history(message):
    history = load_history()
    if not history:
        bot.reply_to(message, "📭 История пуста. Напиши что-нибудь!")
        return
    
    # Показываем последние 10 сообщений
    recent = history[-10:]
    response = "📜 ПОСЛЕДНИЕ СООБЩЕНИЯ:\n\n"
    for msg in recent:
        response += f"• {msg}\n"
    
    bot.reply_to(message, response)

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

# ================= ОБРАБОТКА ОБЫЧНЫХ СООБЩЕНИЙ =================
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    # Игнорируем команды и кнопки
    if message.text.startswith('/'):
        return
    
    # Показываем статус "печатает"
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Генерируем ответ
        reply = generate_response(message.text)
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        reply = "😅 Извини, я немного устал. Давай еще раз?"
    
    bot.reply_to(message, reply)

# ================= ЗАПУСК =================
if __name__ == "__main__":
    print("🤖 Бот запущен! Нажми Ctrl+C для остановки.")
    print(f"📊 Модель: {MODEL_NAME}")
    print(f"📁 Список дел: {TODO_FILE}")
    print(f"📁 История: {HISTORY_FILE}")
    bot.infinity_polling()