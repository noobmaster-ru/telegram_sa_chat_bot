import json
import logging
import re
from urllib import error, parse, request

from axiomai.config import SuperbankingConfig
from axiomai.constants import URL_CONFIRM_PAYMENT, URL_CREATE_PAYMENT, URL_SIGN_PAYMENT

logger = logging.getLogger(__name__)

BANK_ALIASES: dict[str, str] = {
    "сбер": "SBER",
    "сбербанк": "SBER",
    "сбер банк": "SBER",
    "сбер-банк": "SBER",
    "сбер- банк": "SBER",
    "сбер -банк": "SBER",
    "сбер - банк": "SBER",
    "тинько": "TINKOFF",
    "тинькофф": "TINKOFF",
    "тинькоф": "TINKOFF",
    "тиньков": "TINKOFF",
    "тиньковв": "TINKOFF",
    "тинек": "TINKOFF",
    "тинёк": "TINKOFF",
    "тиньк": "TINKOFF",
    "тинь": "TINKOFF",
    "тбанк": "TINKOFF",
    "т-банк": "TINKOFF",
    "т- банк": "TINKOFF",
    "т -банк": "TINKOFF",
    "т банк": "TINKOFF",
    "т - банк": "TINKOFF",
    "альф": "ALFA",
    "альфа": "ALFA",
    "альфабанк": "ALFA",
    "альфа-банк": "ALFA",
    "альфа- банк": "ALFA",
    "альфа -банк": "ALFA",
    "альфа - банк": "ALFA",
    "втб": "VTB",
    "втб банк": "VTB",
    "втб - банк": "VTB",
    "втб- банк": "VTB",
    "втб -банк": "VTB",
    "озон": "OZON",
    "азон": "OZON",
    "озон банк": "OZON",
    "азон банк": "OZON",
    "ozon": "OZON",
    "газпромбанк": "Gazprombank",
    "газпром- банк": "Gazprombank",
    "газпром -банк": "Gazprombank",
    "газпром - банк": "Gazprombank",
    "райффайзен банк": "RAIFFEISEN",
    "райффайзен": "RAIFFEISEN",
    "райфайзен банк": "RAIFFEISEN",
    "райфайзен": "RAIFFEISEN",
    "райф": "RAIFFEISEN",
    "райфф": "RAIFFEISEN",
    "росбанк": "ROSBANK",
    "рос банк": "ROSBANK",
    "открытие": "OTKRITIE",
    "почтабанк": "POST BANK",
    "почта-банк": "POST BANK",
    "почта- банк": "POST BANK",
    "почта -банк": "POST BANK",
    "почта - банк": "POST BANK",
    "почта банк": "POST BANK",
    "отп": "OTP BANK",
    "отп банк": "OTP BANK",
    "отп-банк": "OTP BANK",
    "отп- банк": "OTP BANK",
    "отп - банк": "OTP BANK",
    "отп -банк": "OTP BANK",
    "совкомбанк": "Sovcombank",
    "совком банк": "Sovcombank",
    "совком": "Sovcombank",
    "мтс": "MTS Bank",
    "мтсбанк": "MTS Bank",
    "мтс банк": "MTS Bank",
    "мтс-банк": "MTS Bank",
    "мтс- банк": "MTS Bank",
    "мтс -банк": "MTS Bank",
    "мтс - банк": "MTS Bank",
    "яндекс": "YANDEX BANK",
    "яндексбанк": "YANDEX BANK",
    "яндекс банк": "YANDEX BANK",
    "yandex": "YANDEX BANK",
    "вб": "Wildberries Bank",
    "вббанк": "Wildberries Bank",
    "вб банк": "Wildberries Bank",
    "вб-банк": "Wildberries Bank",
    "вб -банк": "Wildberries Bank",
    "вб- банк": "Wildberries Bank",
    "вб - банк": "Wildberries Bank",
    "wb": "Wildberries Bank",
    "wbбанк": "Wildberries Bank",
    "wb банк": "Wildberries Bank",
    "wildberries": "Wildberries Bank",
    "толчка": "TOCHKA BANK",
    "точка": "TOCHKA BANK",
    "точкабанк": "TOCHKA BANK",
    "точка-банк": "TOCHKA BANK",
    "точка- банк": "TOCHKA BANK",
    "точка -банк": "TOCHKA BANK",
    "точка - банк": "TOCHKA BANK",
}


class Superbanking:
    def __init__(self, superbanking_config: SuperbankingConfig) -> None:
        self._superbanking_config = superbanking_config

        with open("./assets/superbanking.json") as f:
            self._superbanking_banks = json.loads(f.read())

        # "TINKOFF": T-Банк
        self._bank_name_map: dict[str, str] = {
            bank["bankName"].upper(): bank["nameRus"] for bank in self._superbanking_banks
        }

    def get_bank_name_rus(self, bank_alias: str) -> str | None:
        normalized = re.sub(r"[\s\-]", "", bank_alias.lower())
        bank_name = BANK_ALIASES.get(normalized)
        if bank_name:
            return self._bank_name_map.get(bank_name.upper())
        return None

    @staticmethod
    def _convert_phone_number_to_superbanking_format(phone_number: str) -> str:
        digits = re.sub(r"\D", "", phone_number)
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        return f"00{digits}"

    def _get_bank_identifier_by_bank_name_rus(self, bank_name_rus: str) -> str | None:
        normalized = re.sub(r"[\s\-]", "", bank_name_rus.lower())
        if bank_name := BANK_ALIASES.get(normalized):
            for bank in self._superbanking_banks:
                if str(bank.get("bankName", "")).strip().upper() == bank_name.upper():
                    return bank.get("identifier")

        normalized_name_rus = bank_name_rus.strip().lower()
        for bank in self._superbanking_banks:
            if str(bank.get("nameRus", "")).strip().lower() == normalized_name_rus:
                return bank.get("identifier")
        return None

    def create_payment(self, phone_number: str, bank_name_rus: str, amount: int, order_number: str) -> str:
        phone_number_superbanking_format = self._convert_phone_number_to_superbanking_format(phone_number=phone_number)
        bank_identifier = self._get_bank_identifier_by_bank_name_rus(bank_name_rus=bank_name_rus)
        if not bank_identifier:
            message = f"Unknown bank: {bank_name_rus}"
            raise ValueError(message)

        payload = {
            "cabinetId": self._superbanking_config.cabinet_id,
            "projectId": self._superbanking_config.project_id,
            "clearingCenterId": self._superbanking_config.clearing_center_id,
            "orderNumber": order_number,
            "phone": phone_number_superbanking_format,
            "bank": bank_identifier,
            "amount": amount,
            "purposePayment": "Выплата кэшбека",
            "comment": "Выплата кэшбека",
        }

        try:
            response_data = self._post_json(
                url=URL_CREATE_PAYMENT,
                payload=payload,
                log_context="create payout",
                order_number=order_number,
            )
            cabinet_transaction_id = self._extract_cabinet_transaction_id(response_data)
            return str(cabinet_transaction_id)

        except Exception:
            logger.exception(
                "Superbanking create_payment() failed for order_number=%s",
                order_number,
            )
            raise

    def sign_payment(self, cabinet_transaction_id: str, order_number: str) -> bool:
        try:
            payload = {
                "cabinetId": self._superbanking_config.cabinet_id,
                "cabinetTransactionId": cabinet_transaction_id,
            }
            response_data = self._post_json(
                url=URL_SIGN_PAYMENT,
                payload=payload,
                log_context="sign payout",
                order_number=order_number,
                add_idempotency_token=True,
            )
            return self._extract_sign_result(response_data)
        except Exception:
            logger.exception(
                "Superbanking sign_payment() failed for cabinet_transaction_id=%s, order_number=%s",
                cabinet_transaction_id,
                order_number,
            )
            raise

    def confirm_operation(self, order_number: str) -> str:
        try:
            payload = {
                "cabinetId": self._superbanking_config.cabinet_id,
                "orderNumber": order_number,
            }
            response_data = self._post_json(
                url=URL_CONFIRM_PAYMENT,
                payload=payload,
                log_context="confirm operation",
                add_idempotency_token=False,
            )
            return self._extract_confirm_url(response_data)
        except Exception:
            logger.exception("Superbanking confirm_operation() failed for order_number=%s", order_number)
            raise

    def _post_json(
        self,
        url: str,
        payload: dict,
        log_context: str,
        *,
        order_number: str | None = None,
        add_idempotency_token: bool = True,
    ) -> dict:
        parsed_url = parse.urlparse(url)
        if parsed_url.scheme != "https":
            raise ValueError(f"Unsupported URL scheme: {parsed_url.scheme}")
        req = request.Request(  # noqa: S310
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        req.add_header("x-token-user-api", self._superbanking_config.api_key)
        if add_idempotency_token and order_number:
            req.add_header("x-idempotency-token", order_number)

        try:
            with request.urlopen(req, timeout=30) as response:  # noqa: S310
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            error_body = exc.read().decode("utf-8") if exc.fp else ""
            logger.exception(
                "Superbanking %s failed with status %s. Body: %s",
                log_context,
                exc.code,
                error_body,
            )
            raise
        except error.URLError:
            logger.exception("Superbanking %s request failed", log_context)
            raise

        return json.loads(body) if body else {}

    @staticmethod
    def _extract_cabinet_transaction_id(response_data: dict) -> str:
        data = response_data.get("data") if isinstance(response_data.get("data"), dict) else None
        payout = data.get("payout") if isinstance(data, dict) else None
        cabinet_transaction_id = payout.get("id") if isinstance(payout, dict) else None
        if cabinet_transaction_id is None:
            message = f"Unexpected Superbanking response: {response_data}"
            raise ValueError(message)
        return str(cabinet_transaction_id)

    @staticmethod
    def _extract_sign_result(response_data: dict) -> bool:
        result = response_data.get("result")
        if isinstance(result, bool):
            return result
        message = f"Unexpected Superbanking sign response: {response_data}"
        raise ValueError(message)

    @staticmethod
    def _extract_confirm_url(response_data: dict) -> str:
        data = response_data.get("data") if isinstance(response_data.get("data"), dict) else None
        chect_url = data.get("url") if isinstance(data, dict) else None
        if not chect_url:
            message = f"Unexpected Superbanking confirm response: {response_data}"
            raise ValueError(message)
        return chect_url
