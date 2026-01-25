import json

from aiogoogle import Aiogoogle, HTTPError
from aiogoogle.auth.creds import ServiceAccountCreds

from axiomai.application.dto import CashbackArticle
from axiomai.application.exceptions.cashback_table import WritePermissionError
from axiomai.config import Config


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
                if err.res.status_code == 404:
                    raise PermissionError(
                        "The service account does not have access to the provided Google Sheets document. "
                        "Please share the document with the service account email."
                    ) from err
                if err.res.status_code == 403:
                    raise WritePermissionError(
                        "The service account does not have write access to the Google Sheets document."
                    )
                else:
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
                sheets_v4.spreadsheets.values.get(spreadsheetId=table_id, range="D2:H")
            )

            values = response.get("values", [])
            articles = []
            for row in values:
                if row and len(row) >= 1 and row[0]:
                    try:
                        nm_id = int(row[0])
                        image_url = row[1] if len(row) >= 2 else ""
                        title = row[2] if len(row) >= 3 else ""
                        brand_name = row[3] if len(row) >= 4 else ""
                        instruction_text = row[4] if len(row) >= 5 else ""
                        articles.append(
                            CashbackArticle(
                                nm_id=nm_id,
                                title=title,
                                brand_name=brand_name,
                                instruction_text=instruction_text,
                                image_url=image_url,
                            )
                        )
                    except ValueError:
                        continue

            return articles
