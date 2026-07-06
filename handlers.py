import telebot
from telebot import types
from datetime import datetime
import io
import matplotlib.pyplot as plt
from config import Config
from storage import Database
from ai import AIModel, get_compliment, get_joke, get_riddle
from keyboards import main_menu, mode_selection, confirm_clear

class Handlers:
    def __init__(self, bot: telebot.TeleBot, db: Database, ai: AIModel):
        self.bot = bot
        self.db = db
        self.ai = ai
        self.riddle_mode = {}
        self.current_riddle = {}
        self._register_handlers()
    
    def _register_handlers(self):
        # Команды
        self.bot.message_handler(commands=['start', 'help'])(self.start)
        self.bot.message_handler(commands=['mode'])(self.change_mode)
        
        # Список дел
        self.bot.message_handler(commands=['add'])(self.add_todo)
        self.bot.message_handler(commands=['list'])(self.list_todos)
        self.bot.message_handler(commands=['done'])(self.done_todo)
        self.bot.message_handler(commands=['delete'])(self.delete_todo)
        self.bot.message_handler(commands=['clear'])(self.clear_todos)
        
        # Кормления
        self.bot.message_handler(commands=['feed'])(self.add_feeding)
        self.bot.message_handler(commands=['feeding'])(self.show_feeding)
        self.bot.message_handler(commands=['feedstats'])(self.feeding_stats)
        self.bot.message_handler(commands=['feedchart'])(self.feeding_chart)
        self.bot.message_handler(commands=['clearfeeding'])(self.clear_feeding)
        
        # Кнопки
        self.bot.message_handler(func=lambda m: m.text == "📋 Список дел")(self.list_todos)
        self.bot.message_handler(func=lambda m: m.text == "➕ Добавить дело")(self.add_todo_prompt)
        self.bot.message_handler(func=lambda m: m.text == "✅ Выполнено")(self.done_prompt)
        self.bot.message_handler(func=lambda m: m.text == "🍼 Кормления")(self.show_feeding)
        self.bot.message_handler(func=lambda m: m.text == "➕ Записать кормление")(self.add_feeding_prompt)
        self.bot.message_handler(func=lambda m: m.text == "📊 Статистика")(self.feeding_stats)
        self.bot.message_handler(func=lambda m: m.text == "📈 График")(self.feeding_chart)
        self.bot.message_handler(func=lambda m: m.text == "🗑️ Очистить кормления")(self.clear_feeding)
        self.bot.message_handler(func=lambda m: m.text == "💝 Комплимент")(self.send_compliment)
        self.bot.message_handler(func=lambda m: m.text == "😂 Шутка")(self.send_joke)
        self.bot.message_handler(func=lambda m: m.text == "🧩 Загадка")(self.send_riddle)
        self.bot.message_handler(func=lambda m: m.text == "🎭 Сменить режим")(self.change_mode_prompt)
        self.bot.message_handler(func=lambda m: m.text == "📚 Помощь")(self.show_help)
        
        # Обработка обычных сообщений
        self.bot.message_handler(func=lambda m: True)(self.handle_message)
        
        # Callback-запросы
        self.bot.callback_query_handler(func=lambda call: True)(self.handle_callback)
    
    # ================= СТАРТ И ПОМОЩЬ =================
    def start(self, message):
        chat_id = message.chat.id
        mode = self.db.get_mode(chat_id)
        mode_name = Config.MODES.get(mode, Config.MODES["family"])["name"]
        
        greeting = f"""
👋 **Привет! Я {Config.BOT_NAME}** {Config.BOT_EMOJI}

🎭 **Текущий режим:** {mode_name}

🍼 Ведите дневник кормлений дочки
📋 Управляйте общим списком дел
🎮 Играйте и развлекайтесь

**Используй кнопки ниже или команды!**
        """
        self.bot.reply_to(message, greeting, parse_mode="Markdown", reply_markup=main_menu())
    
    def show_help(self, message):
        help_text = """
📚 **Семейный помощник — все команды**

**📋 Список дел:**
/add <текст> - добавить дело
/list - показать список
/done <номер> - отметить выполненным
/delete <номер> - удалить дело
/clear - очистить список

**🍼 Дневник кормлений:**
/feed <мл> - записать кормление
/feed <мл> <комментарий> - с комментарием
/feeding - показать сегодняшние кормления
/feedstats - статистика за день
/feedchart - график за 7 дней
/clearfeeding - очистить все записи

**🎮 Развлечения:**
Напиши: комплимент, шутка, загадка

**🎭 Режимы:**
/mode family - семейный
/mode funny - веселый
/mode strict - деловой
/mode child - детский
        """
        self.bot.reply_to(message, help_text, parse_mode="Markdown")
    
    # ================= СПИСОК ДЕЛ =================
    def add_todo(self, message):
        chat_id = message.chat.id
        text = message.text.replace('/add', '').strip()
        if not text:
            self.bot.reply_to(message, "❌ Напиши дело после команды.\nПример: /add Купить молоко")
            return
        self.db.add_todo(chat_id, text)
        self.bot.reply_to(message, f"✅ Добавлено: {text}")
    
    def add_todo_prompt(self, message):
        self.bot.reply_to(message, "✏️ Напиши /add <текст дела>\nПример: /add Купить продукты")
    
    def list_todos(self, message):
        chat_id = message.chat.id
        todos = self.db.get_todos(chat_id)
        if not todos:
            self.bot.reply_to(message, "📭 Список дел пуст!")
            return
        
        response = "📋 **ТВОЙ СПИСОК ДЕЛ:**\n\n"
        for todo in todos:
            status = "✅" if todo['done'] else "⬜"
            response += f"{todo['id']}. {status} {todo['text']}\n"
        
        self.bot.reply_to(message, response, parse_mode="Markdown")
    
    def done_todo(self, message):
        chat_id = message.chat.id
        try:
            parts = message.text.split()
            if len(parts) < 2:
                self.bot.reply_to(message, "❌ Используй: /done <номер>")
                return
            todo_id = int(parts[1])
            if self.db.mark_todo_done(todo_id, chat_id):
                self.bot.reply_to(message, "✅ Дело выполнено! 🎉")
            else:
                self.bot.reply_to(message, f"❌ Дела с номером {todo_id} нет.")
        except ValueError:
            self.bot.reply_to(message, "❌ Номер должен быть числом.")
    
    def done_prompt(self, message):
        self.bot.reply_to(message, "✏️ Напиши /done <номер>\nПример: /done 3")
    
    def delete_todo(self, message):
        chat_id = message.chat.id
        try:
            parts = message.text.split()
            if len(parts) < 2:
                self.bot.reply_to(message, "❌ Используй: /delete <номер>")
                return
            todo_id = int(parts[1])
            if self.db.delete_todo(todo_id, chat_id):
                self.bot.reply_to(message, "🗑️ Дело удалено!")
            else:
                self.bot.reply_to(message, f"❌ Дела с номером {todo_id} нет.")
        except ValueError:
            self.bot.reply_to(message, "❌ Номер должен быть числом.")
    
    def clear_todos(self, message):
        chat_id = message.chat.id
        self.bot.reply_to(message, "⚠️ Удалить все дела?", reply_markup=confirm_clear())
    
    # ================= КОРМЛЕНИЯ =================
    def add_feeding(self, message):
        chat_id = message.chat.id
        try:
            parts = message.text.split()
            if len(parts) < 2:
                self.bot.reply_to(message, "❌ Укажи объем в мл.\nПример: /feed 120\nМожно с комментарием: /feed 120 отлично поела")
                return
            ml = int(parts[1])
            comment = " ".join(parts[2:]) if len(parts) > 2 else ""
            self.db.add_feeding(chat_id, ml, comment)
            self.bot.reply_to(message, f"✅ Записано кормление: **{ml} мл**\n🕐 {datetime.now().strftime('%H:%M')}{f' ({comment})' if comment else ''}", parse_mode="Markdown")
        except ValueError:
            self.bot.reply_to(message, "❌ Объем должен быть числом.\nПример: /feed 120")
    
    def add_feeding_prompt(self, message):
        self.bot.reply_to(message, "✏️ Напиши объем в мл:\n/feed 120\n\nМожно добавить комментарий:\n/feed 120 отлично поела")
    
    def show_feeding(self, message):
        chat_id = message.chat.id
        feedings = self.db.get_feedings_today(chat_id)
        
        if not feedings:
            self.bot.reply_to(message, "🍼 Сегодня кормлений еще не было!\nЧтобы добавить: /feed 120")
            return
        
        response = "🍼 **ДНЕВНИК КОРМЛЕНИЙ**\n"
        response += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
        
        total = 0
        for i, entry in enumerate(feedings, 1):
            total += entry['ml']
            response += f"{i}. 🕐 {entry['time']} — **{entry['ml']} мл**"
            if entry['comment']:
                response += f" ({entry['comment']})"
            response += "\n"
        
        response += f"\n📊 **Всего за день: {total} мл**"
        self.bot.reply_to(message, response, parse_mode="Markdown")
    
    def feeding_stats(self, message):
        chat_id = message.chat.id
        feedings = self.db.get_feedings_today(chat_id)
        
        if not feedings:
            self.bot.reply_to(message, "📭 Нет данных о кормлениях за сегодня.")
            return
        
        total = sum(f['ml'] for f in feedings)
        avg = total / len(feedings) if feedings else 0
        max_ml = max(f['ml'] for f in feedings) if feedings else 0
        
        response = "📊 **СТАТИСТИКА КОРМЛЕНИЙ**\n\n"
        response += f"📅 Сегодня: {datetime.now().strftime('%d.%m.%Y')}\n"
        response += f"🍼 Количество: **{len(feedings)}**\n"
        response += f"📈 Всего: **{total} мл**\n"
        response += f"📊 Средний объем: **{int(avg)} мл**\n"
        response += f"🔥 Максимум: **{max_ml} мл**\n"
        
        if total > 500:
            response += "\n💪 Отличный аппетит! Дочка молодец! 🌟"
        elif total > 300:
            response += "\n👍 Неплохо! Так держать!"
        else:
            response += "\n😊 Мало, но вкусно! Попробуйте предложить еще позже."
        
        self.bot.reply_to(message, response, parse_mode="Markdown")
    
    def feeding_chart(self, message):
        chat_id = message.chat.id
        daily_data = self.db.get_feedings_last_days(chat_id, 7)
        
        if not any(daily_data.values()):
            self.bot.reply_to(message, "📭 Нет данных для графика.")
            return
        
        # Строим график
        dates = list(daily_data.keys())
        values = list(daily_data.values())
        
        plt.figure(figsize=(10, 5))
        plt.bar(range(len(dates)), values, color='skyblue', alpha=0.7)
        plt.plot(range(len(dates)), values, marker='o', color='darkblue', linestyle='-', linewidth=2)
        plt.xticks(range(len(dates)), [datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m") for d in dates], rotation=45)
        plt.xlabel('Дата')
        plt.ylabel('Объем (мл)')
        plt.title('Динамика кормлений за последние 7 дней')
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        
        for i, v in enumerate(values):
            plt.text(i, v + 5, str(v), ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close()
        
        self.bot.send_photo(message.chat.id, buf, caption="📈 **Динамика кормлений за последние 7 дней**", parse_mode="Markdown")
    
    def clear_feeding(self, message):
        self.bot.reply_to(message, "⚠️ Удалить ВСЕ записи кормлений?", reply_markup=confirm_clear())
    
    # ================= РАЗВЛЕЧЕНИЯ =================
    def send_compliment(self, message):
        self.bot.reply_to(message, get_compliment())
    
    def send_joke(self, message):
        self.bot.reply_to(message, get_joke())
    
    def send_riddle(self, message):
        chat_id = message.chat.id
        question, answer = get_riddle()
        self.riddle_mode[chat_id] = True
        self.current_riddle[chat_id] = answer
        self.bot.reply_to(message, f"❓ Загадка: {question}\n\nОтправь свой ответ!")
    
    # ================= РЕЖИМЫ =================
    def change_mode(self, message):
        parts = message.text.split()
        if len(parts) < 2:
            self.bot.reply_to(message, "🎭 Выбери режим:\n/mode family - Семейный\n/mode funny - Веселый\n/mode strict - Деловой\n/mode child - Детский")
            return
        
        mode = parts[1]
        if mode in Config.MODES:
            chat_id = message.chat.id
            self.db.set_mode(chat_id, mode)
            mode_name = Config.MODES[mode]["name"]
            self.bot.reply_to(message, f"✅ Режим изменен на **{mode_name}**!", parse_mode="Markdown")
        else:
            self.bot.reply_to(message, f"❌ Режим '{mode}' не найден.")
    
    def change_mode_prompt(self, message):
        self.bot.reply_to(message, "🎭 Выбери режим:", reply_markup=mode_selection())
    
    # ================= ОБЫЧНЫЕ СООБЩЕНИЯ =================
    def handle_message(self, message):
        chat_id = message.chat.id
        
        # Проверяем загадку
        if self.riddle_mode.get(chat_id, False):
            answer = self.current_riddle.get(chat_id)
            if answer and message.text.lower().strip() == answer.lower():
                self.riddle_mode[chat_id] = False
                self.current_riddle[chat_id] = None
                self.bot.reply_to(message, f"🎉 Правильно! Ты супер-умный! 💪")
                return
            elif answer:
                self.bot.reply_to(message, f"🤔 Не угадал! Попробуй еще раз.\nПодсказка: слово начинается на букву '{answer[0].upper()}'")
                return
        
        # Обработка специальных команд
        text_lower = message.text.lower()
        if text_lower in ["комплимент", "похвали"]:
            self.bot.reply_to(message, get_compliment())
            return
        elif text_lower in ["шутка", "смеш"]:
            self.bot.reply_to(message, get_joke())
            return
        elif text_lower == "загадка":
            question, answer = get_riddle()
            self.riddle_mode[chat_id] = True
            self.current_riddle[chat_id] = answer
            self.bot.reply_to(message, f"❓ Загадка: {question}\n\nОтправь свой ответ!")
            return
        
        # Генерация ответа через ИИ
        mode = self.db.get_mode(chat_id)
        self.bot.send_chat_action(message.chat.id, 'typing')
        reply = self.ai.generate_response(message.text, mode)
        self.bot.reply_to(message, reply)
    
    # ================= CALLBACK-ЗАПРОСЫ =================
    def handle_callback(self, call):
        chat_id = call.message.chat.id
        
        if call.data.startswith("mode_"):
            mode = call.data.replace("mode_", "")
            if mode in Config.MODES:
                self.db.set_mode(chat_id, mode)
                mode_name = Config.MODES[mode]["name"]
                self.bot.answer_callback_query(call.id, f"✅ Режим изменен на {mode_name}!")
                self.bot.edit_message_text(f"✅ Режим изменен на **{mode_name}**!", chat_id, call.message.message_id, parse_mode="Markdown")
        
        elif call.data == "clear_yes":
            # Очищаем дела и кормления
            self.db.clear_todos(chat_id)
            self.db.clear_feedings(chat_id)
            self.bot.answer_callback_query(call.id, "✅ Все данные очищены!")
            self.bot.edit_message_text("🗑️ Все данные очищены!", chat_id, call.message.message_id)
        
        elif call.data == "clear_no":
            self.bot.answer_callback_query(call.id, "❌ Отменено")
            self.bot.edit_message_text("✅ Очистка отменена", chat_id, call.message.message_id)