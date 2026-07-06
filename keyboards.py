from telebot import types

def main_menu():
    """Главное меню с кнопками"""
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
    btn12 = types.KeyboardButton("🎭 Сменить режим")
    btn13 = types.KeyboardButton("📚 Помощь")
    
    markup.add(btn1, btn2, btn3)
    markup.add(btn4, btn5, btn6)
    markup.add(btn7, btn8)
    markup.add(btn9, btn10, btn11)
    markup.add(btn12, btn13)
    
    return markup

def feeding_volume_keyboard():
    """Клавиатура для выбора объема кормления"""
    markup = types.ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    
    btn1 = types.KeyboardButton("50 мл")
    btn2 = types.KeyboardButton("80 мл")
    btn3 = types.KeyboardButton("100 мл")
    btn4 = types.KeyboardButton("120 мл")
    btn5 = types.KeyboardButton("150 мл")
    btn6 = types.KeyboardButton("200 мл")
    btn7 = types.KeyboardButton("✏️ Свой объем")
    btn8 = types.KeyboardButton("🔙 Назад в меню")
    
    markup.add(btn1, btn2, btn3)
    markup.add(btn4, btn5, btn6)
    markup.add(btn7, btn8)
    
    return markup

def back_to_menu_keyboard():
    """Клавиатура только с кнопкой 'Назад'"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 Назад в меню"))
    return markup

def mode_selection():
    """Клавиатура для выбора режима"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👨‍👩‍👧‍👦 Семейный", callback_data="mode_family"),
        types.InlineKeyboardButton("🤪 Веселый", callback_data="mode_funny"),
        types.InlineKeyboardButton("📌 Деловой", callback_data="mode_strict"),
        types.InlineKeyboardButton("🌈 Детский", callback_data="mode_child")
    )
    return markup

def confirm_clear():
    """Подтверждение очистки"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Да, очистить", callback_data="clear_yes"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="clear_no")
    )
    return markup
