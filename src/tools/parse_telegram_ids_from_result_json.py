from __future__ import annotations

import json
import zipfile
from io import BytesIO
from typing import Set, Dict, Any, List

def parse_zipped_result_json(file_bytes: bytes) -> Set[int]:
    """
    Принимает содержимое ZIP-файла (bytes), находит внутри JSON
    (например, result.json), парсит его и возвращает множество user_id.
    """
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as z:
            # ищем любой .json, при желании можно сузить до "result.json"
            json_names = [name for name in z.namelist() if name.endswith(".json")]

            if not json_names:
                raise ValueError("В архиве не найден ни один JSON-файл")

            json_name = json_names[0]

            with z.open(json_name) as f:
                data = json.load(f)

        return parse_telegram_ids_from_json_data(data)

    except zipfile.BadZipFile as e:
        raise ValueError("Файл не является корректным ZIP-архивом") from e
    except json.JSONDecodeError as e:
        raise ValueError("Не удалось прочитать JSON из архива") from e


def parse_telegram_ids_from_json_data(data: Dict[str, Any]) -> Set[int]:
    """
    Принимает словарь из result.json и возвращает множество user_id
    всех личных чатов (type == "personal_chat").
    """
    chats: List[Dict[str, Any]] = data.get("chats", {}).get("list", [])
    ids: Set[int] = set()

    for chat in chats:
        if chat.get("type") == "personal_chat":
            chat_id = chat.get("id")
            if chat_id is not None:
                try:
                    ids.add(int(chat_id))
                except (TypeError, ValueError):
                    # Можно залогировать, если нужно
                    continue

    return ids