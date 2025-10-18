import sqlite3
from pathlib import Path
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "users.db")

def init_db():
    """Создаёт таблицу пользователей, если её нет"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER UNIQUE,
                        username TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''')
    conn.close()
    # cur = conn.cursor()
    # cur.execute("""
    #     CREATE TABLE IF NOT EXISTS users (
    #         id INTEGER PRIMARY KEY
    #     )
    # """)
    # conn.commit()
    # conn.close()


def user_exists(user_id: int) -> bool:
    """Проверяет, есть ли пользователь в базе"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def add_user(user_id: int):
    """Добавляет пользователя в базу"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_user_count() -> int:
    """Возвращает количество пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    conn.close()
    return count