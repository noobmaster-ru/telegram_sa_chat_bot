# здесь будет бд
import sqlite3
from typing import List, Dict

DB_PATH = "db/chat_history.db"


def init_history_db():
    """Создаёт таблицу, если её нет."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()


def add_message(telegram_id: int, role: str, content: str):
    """Сохраняет сообщение (user или assistant)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO chat_history (telegram_id, role, content) VALUES (?, ?, ?)",
            (telegram_id, role, content)
        )
        conn.commit()


def get_chat_history(telegram_id: int, limit: int = 10) -> List[Dict[str, str]]:
    """Возвращает последние N сообщений в формате [{'role': 'user', 'content': '...'}, ...]"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT role, content FROM chat_history WHERE telegram_id = ? ORDER BY id DESC LIMIT ?",
            (telegram_id, limit)
        )
        rows = cursor.fetchall()

    # Возвращаем в правильном порядке (от старых к новым)
    return [{"role": r, "content": c} for r, c in reversed(rows)]