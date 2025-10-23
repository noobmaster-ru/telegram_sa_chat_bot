import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT"),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )


def init_history_db():
    """Создаёт таблицу, если её нет."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)
        conn.commit()


def add_message(telegram_id: int, role: str, content: str):
    """Сохраняет сообщение."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_history (telegram_id, role, content) VALUES (%s, %s, %s);",
                (telegram_id, role, content)
            )
        conn.commit()


def get_chat_history(telegram_id: int, limit: int = 10) -> List[Dict[str, str]]:
    """Возвращает последние N сообщений."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT role, content FROM chat_history WHERE telegram_id = %s ORDER BY id DESC LIMIT %s;",
                (telegram_id, limit)
            )
            rows = cur.fetchall()

    # Возвращаем в порядке от старых к новым
    return list(reversed(rows))