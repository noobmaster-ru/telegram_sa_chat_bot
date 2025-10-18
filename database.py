import sqlite3
from pathlib import Path

DB_PATH = Path("users.db")

def init_db():
    """Создаёт таблицу пользователей, если её нет"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()


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