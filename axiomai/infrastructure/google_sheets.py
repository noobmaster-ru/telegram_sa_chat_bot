import json
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any

from aiogoogle import Aiogoogle, HTTPError
from aiogoogle.auth.creds import ServiceAccountCreds

from axiomai.application.dto import CashbackArticle
from axiomai.application.exceptions.cashback_table import WritePermissionError
from axiomai.config import Config
from axiomai.infrastructure.database.models import Buyer

logger = logging.getLogger(__name__)
MSK_TZ = timezone(timedelta(hours=3))


class GoogleSheetsGateway:
    def __init__(self, config: Config) -> None:
        with open(config.service_account_axiomai) as f:
            service_account_key = json.load(f)

        self._service_account_email = service_account_key["client_email"]

        self._credentials = ServiceAccountCreds(
            **service_account_key,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        self._aiogoogle = Aiogoogle(service_account_creds=self._credentials)

    async def ensure_service_account_added(self, table_id: str) -> None:
        async with self._aiogoogle as aiogoogle:
            drive_v3 = await aiogoogle.discover("drive", "v3")

            try:
                permissions = await aiogoogle.as_service_account(
                    drive_v3.permissions.list(fileId=table_id, fields="permissions(emailAddress,role)")
                )
            except HTTPError as err:
                if err.res.status_code == 404:  # noqa: PLR2004
                    raise PermissionError(
                        "The service account does not have access to the provided Google Sheets document. "
                        "Please share the document with the service account email."
                    ) from err
                if err.res.status_code == 403:  # noqa: PLR2004
                    raise WritePermissionError(
                        "The service account does not have write access to the Google Sheets document."
                    ) from err
                raise

            for permission in permissions.get("permissions", []):
                if permission.get("emailAddress") == self._service_account_email:
                    if permission.get("role") not in ("writer", "owner"):
                        raise WritePermissionError(
                            "The service account does not have write access to the Google Sheets document."
                        )
                    return

    async def get_cashback_articles(self, table_id: str) -> list[CashbackArticle]:
        async with self._aiogoogle as aiogoogle:
            sheets_v4 = await aiogoogle.discover("sheets", "v4")

            response = await aiogoogle.as_service_account(
                sheets_v4.spreadsheets.values.get(spreadsheetId=table_id, range="D2:I")
            )

            values = response.get("values", [])
            articles = []
            for row in values:
                if row and len(row) >= 2 and row[1]:  # noqa: PLR2004
                    try:
                        in_stock = row[0].upper() == "TRUE" if row[0] else False
                        nm_id = int(row[1])
                        image_url = row[2] if len(row) >= 3 else ""  # noqa:  PLR2004
                        title = row[3] if len(row) >= 4 else ""  # noqa: PLR2004
                        brand_name = row[4] if len(row) >= 5 else ""  # noqa: PLR2004
                        instruction_text = row[5] if len(row) >= 6 else ""  # noqa: PLR2004
                    except ValueError:
                        continue

                    articles.append(
                        CashbackArticle(
                            nm_id=nm_id,
                            title=title,
                            brand_name=brand_name,
                            instruction_text=instruction_text,
                            image_url=image_url,
                            in_stock=in_stock,
                        )
                    )

            return articles

    async def sync_buyers_to_sheet(self, table_id: str, buyers: list[Buyer]) -> None:
        """Синхронизирует покупателей в лист "Покупатели" Google Sheets."""
        buyer_index: dict[tuple[int, int], Buyer] = {(b.telegram_id, b.nm_id): b for b in buyers}

        async with self._aiogoogle as aiogoogle:
            sheets_v4 = await aiogoogle.discover("sheets", "v4")

            try:
                await _read_is_paid_manually_from_sheet(aiogoogle, sheets_v4, table_id, buyer_index)
                rows = [_buyer_to_row(buyer) for buyer in buyers]
                await _write_buyers_to_sheet(aiogoogle, sheets_v4, table_id, rows)
            except HTTPError as err:
                logger.exception("Failed to sync buyers to table.id = %s", table_id, exc_info=err)

async def _read_is_paid_manually_from_sheet(
    aiogoogle: Aiogoogle, sheets_v4: Any, table_id: str, buyer_index: dict[tuple[int, int], Buyer]
) -> None:
    """Читает значения is_paid_manually из колонки P и обновляет объекты Buyer."""
    existing_response = await aiogoogle.as_service_account(
        sheets_v4.spreadsheets.values.get(spreadsheetId=table_id, range="Покупатели!B2:P")
    )
    existing_values = existing_response.get("values", [])

    for row in existing_values:
        if len(row) < 6:  # noqa: PLR2004
            continue
        with suppress(ValueError, IndexError):
            telegram_id = int(row[0])  # B - telegram_id
            nm_id = int(row[5])  # G - nm_id (индекс 5 относительно B)
            is_paid_manually = row[14] == "TRUE"
            key = (telegram_id, nm_id)
            if key in buyer_index:
                buyer_index[key].is_paid_manually = is_paid_manually


async def _write_buyers_to_sheet(
    aiogoogle: Aiogoogle, sheets_v4: Any, table_id: str, rows: list[list]
) -> None:
    """Записывает данные покупателей в Google Sheets."""
    spreadsheet = await aiogoogle.as_service_account(
        sheets_v4.spreadsheets.get(
            spreadsheetId=table_id,
            fields="sheets(properties(sheetId,title),conditionalFormats)",
        )
    )
    sheet_id = None
    conditional_formats_count = 0
    for sheet in spreadsheet.get("sheets", []):
        if sheet.get("properties", {}).get("title") == "Покупатели":
            sheet_id = sheet["properties"]["sheetId"]
            conditional_formats_count = len(sheet.get("conditionalFormats", []))
            break

    if sheet_id is None:
        return

    requests = []

    # Удаляем существующие conditional formatting rules (в обратном порядке)
    for i in range(conditional_formats_count - 1, -1, -1):
        requests.append({"deleteConditionalFormatRule": {"sheetId": sheet_id, "index": i}})

    # Очищаем старые данные
    requests.append({
        "updateCells": {
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,
                "startColumnIndex": 0,
                "endColumnIndex": 16,
            },
            "fields": "userEnteredValue,dataValidation",
        }
    })

    if rows:
        # Формируем данные для записи
        row_data = []
        for row in rows:
            cells = [{"userEnteredValue": {"stringValue": str(cell)}} for cell in row[:-1]]
            # Последняя колонка - checkbox (boolean)
            cells.append({"userEnteredValue": {"boolValue": row[-1]}})
            row_data.append({"values": cells})

        requests.append({
            "updateCells": {
                "rows": row_data,
                "start": {"sheetId": sheet_id, "rowIndex": 1, "columnIndex": 0},
                "fields": "userEnteredValue",
            }
        })

        # Data validation для checkbox в колонке P
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": len(rows) + 1,
                    "startColumnIndex": 15,
                    "endColumnIndex": 16,
                },
                "rule": {"condition": {"type": "BOOLEAN"}, "strict": True},
            }
        })

        # Conditional formatting: зеленый фон при checked checkbox
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": sheet_id,
                        "startRowIndex": 1,
                        "endRowIndex": len(rows) + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": 16,
                    }],
                    "booleanRule": {
                        "condition": {
                            "type": "CUSTOM_FORMULA",
                            "values": [{"userEnteredValue": "=$P2=TRUE"}],
                        },
                        "format": {
                            "backgroundColor": {"red": 0.85, "green": 0.95, "blue": 0.85},
                        },
                    },
                },
                "index": 0,
            }
        })

    await aiogoogle.as_service_account(
        sheets_v4.spreadsheets.batchUpdate(spreadsheetId=table_id, json={"requests": requests})
    )


def _buyer_to_row(buyer: Buyer) -> list[str]:
    """Конвертирует Buyer в строку для Google Sheets."""
    first_user_msg_time = ""
    last_user_msg_time = ""
    last_user_msg_text = ""

    if buyer.chat_history:
        user_messages = [msg for msg in buyer.chat_history if "user" in msg and msg.get("user")]
        if user_messages:
            first_msg = user_messages[0]
            last_msg = user_messages[-1]
            first_user_msg_time = _format_time_msk(first_msg.get("created_at", ""))
            last_user_msg_time = _format_time_msk(last_msg.get("created_at", ""))
            last_user_msg_text = last_msg.get("user", "")

    username_link = f"@{buyer.username}" if buyer.username else buyer.fullname

    return [
        username_link,  # A - ссылка на ник
        str(buyer.telegram_id),  # B - telegram_id
        buyer.fullname or "",  # C - fullname
        first_user_msg_time,  # D - первое сообщение
        last_user_msg_time,  # E - последнее сообщение
        last_user_msg_text[:500] if last_user_msg_text else "",  # F - текст последнего сообщения
        str(buyer.nm_id),  # G - nm_id
        "ДА" if buyer.is_ordered else "",  # H - is_ordered
        "ДА" if buyer.is_left_feedback else "",  # I - is_left_feedback
        "ДА" if buyer.is_cut_labels else "",  # J - is_cut_labels
        buyer.phone_number or "",  # K - phone_number
        buyer.bank or "",  # L - bank
        str(buyer.amount) if buyer.amount else "",  # M - amount
        buyer.username or "",  # N - username
        "ДА" if buyer.is_superbanking_paid else "",  # O - is_superbanking_paid
        buyer.is_paid_manually,  # P - is_paid_manually
    ]


def _format_time_msk(iso_time: str) -> str:
    if not iso_time:
        return ""
    try:
        dt = datetime.fromisoformat(iso_time)
        dt_msk = dt.astimezone(MSK_TZ)
        return dt_msk.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return iso_time
