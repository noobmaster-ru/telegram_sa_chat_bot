import json
import logging

from aiogoogle import Aiogoogle, HTTPError
from aiogoogle.auth.creds import ServiceAccountCreds

from axiomai.application.dto import CashbackArticle
from axiomai.application.exceptions.cashback_table import WritePermissionError
from axiomai.config import Config
from axiomai.infrastructure.database.models import Buyer

logger = logging.getLogger(__name__)


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
        rows = []
        for buyer in buyers:
            # Получаем первое и последнее сообщение от пользователя (не от бота)
            first_user_msg_time = ""
            last_user_msg_time = ""
            last_user_msg_text = ""

            if buyer.chat_history:
                user_messages = [msg for msg in buyer.chat_history if "user" in msg and msg.get("user")]
                if user_messages:
                    first_msg = user_messages[0]
                    last_msg = user_messages[-1]
                    first_user_msg_time = first_msg.get("created_at", "")
                    last_user_msg_time = last_msg.get("created_at", "")
                    last_user_msg_text = last_msg.get("user", "")

            username_link = f"@{buyer.username}" if buyer.username else ""

            row = [
                username_link,  # A - ссылка на ник
                str(buyer.telegram_id),  # B - telegram_id
                buyer.fullname or "",  # C - fullname
                first_user_msg_time,  # D - первое сообщение
                last_user_msg_time,  # E - последнее сообщение
                last_user_msg_text[:500] if last_user_msg_text else "",  # F - текст последнего сообщения
                str(buyer.nm_id),  # G - nm_id
                "TRUE" if buyer.is_ordered else "FALSE",  # H - is_ordered
                "TRUE" if buyer.is_left_feedback else "FALSE",  # I - is_left_feedback
                "TRUE" if buyer.is_cut_labels else "FALSE",  # J - is_cut_labels
                buyer.phone_number or "",  # K - phone_number
                buyer.bank or "",  # L - bank
                str(buyer.amount) if buyer.amount else "",  # M - amount
                buyer.username or "",  # N - username
                "TRUE" if buyer.is_superbanking_paid else "FALSE",  # O - is_superbanking_paid
            ]
            rows.append(row)

        async with self._aiogoogle as aiogoogle:
            sheets_v4 = await aiogoogle.discover("sheets", "v4")

            try:
                # Очищаем старые данные (кроме заголовка)
                await aiogoogle.as_service_account(
                    sheets_v4.spreadsheets.values.clear(
                        spreadsheetId=table_id,
                        range="Покупатели!A2:O",
                    )
                )

                # Записываем новые данные
                if rows:
                    await aiogoogle.as_service_account(
                        sheets_v4.spreadsheets.values.update(
                            spreadsheetId=table_id,
                            range="Покупатели!A2:O",
                            valueInputOption="RAW",
                            json={"values": rows},
                        )
                    )
            except HTTPError as err:
                logger.exception("Failed to sync buyers to sheet %s", table_id, exc_info=err)
