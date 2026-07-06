import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """Создает таблицы, если их нет"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Таблица для списка дел
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    done INTEGER DEFAULT 0,
                    created TEXT NOT NULL
                )
            ''')
            
            # Таблица для кормлений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    ml INTEGER NOT NULL,
                    comment TEXT DEFAULT ''
                )
            ''')
            
            # Таблица для настроек чата
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    chat_id INTEGER PRIMARY KEY,
                    mode TEXT DEFAULT 'family',
                    mood TEXT DEFAULT 'neutral'
                )
            ''')
            
            conn.commit()
    
    # ================= СПИСОК ДЕЛ =================
    def get_todos(self, chat_id: int) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, text, done, created FROM todos WHERE chat_id = ? ORDER BY created ASC',
                (chat_id,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def add_todo(self, chat_id: int, text: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO todos (chat_id, text, done, created) VALUES (?, ?, ?, ?)',
                (chat_id, text, 0, datetime.now().isoformat())
            )
            conn.commit()
    
    def mark_todo_done(self, todo_id: int, chat_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE todos SET done = 1 WHERE id = ? AND chat_id = ?',
                (todo_id, chat_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_todo(self, todo_id: int, chat_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM todos WHERE id = ? AND chat_id = ?',
                (todo_id, chat_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_todos(self, chat_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM todos WHERE chat_id = ?', (chat_id,))
            conn.commit()
    
    # ================= КОРМЛЕНИЯ =================
    def get_feedings_today(self, chat_id: int) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, time, ml, comment FROM feedings WHERE chat_id = ? AND date = ? ORDER BY time ASC',
                (chat_id, today)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_feedings_last_days(self, chat_id: int, days: int = 7) -> Dict[str, int]:
        """Возвращает суммы мл по дням за последние N дней"""
        from datetime import timedelta
        result = {}
        for i in range(days - 1, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT SUM(ml) FROM feedings WHERE chat_id = ? AND date = ?',
                    (chat_id, date)
                )
                total = cursor.fetchone()[0] or 0
                result[date] = total
        return result
    
    def add_feeding(self, chat_id: int, ml: int, comment: str = ""):
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO feedings (chat_id, date, time, ml, comment) VALUES (?, ?, ?, ?, ?)',
                (chat_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), ml, comment)
            )
            conn.commit()
    
    def clear_feedings(self, chat_id: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM feedings WHERE chat_id = ?', (chat_id,))
            conn.commit()
    
    # ================= НАСТРОЙКИ =================
    def get_mode(self, chat_id: int) -> str:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT mode FROM settings WHERE chat_id = ?',
                (chat_id,)
            )
            row = cursor.fetchone()
            if row:
                return row[0]
            return 'family'
    
    def set_mode(self, chat_id: int, mode: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO settings (chat_id, mode) VALUES (?, ?)',
                (chat_id, mode)
            )
            conn.commit()