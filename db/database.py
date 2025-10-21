import sqlite3
import os
import shutil

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

def user_exists(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM users WHERE telegram_id = ?", (user_id,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists



def add_user(user_id: int, username: str = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (user_id, username)
    )
    conn.commit()
    conn.close()
