import json
import re

from axiomai.config import SuperbankingConfig

BANK_ALIASES: dict[str, str] = {
    "сбер": "SBER",
    "сбербанк": "SBER",
    "сбер банк": "SBER",
    "сбер-банк": "SBER",
    "тинькофф": "TINKOFF",
    "тинькоф": "TINKOFF",
    "тиньков": "TINKOFF",
    "т-банк": "TINKOFF",
    "т- банк": "TINKOFF",
    "т -банк": "TINKOFF",
    "т банк": "TINKOFF",
    "тбанк": "TINKOFF",
    "тиньк": "TINKOFF",
    "тинек": "TINKOFF",
    "альфа": "ALFA",
    "альфабанк": "ALFA",
    "альфа-банк": "ALFA",
    "втб": "VTB",
    "озон": "OZON",
    "ozon": "OZON",
    "газпромбанк": "Gazprombank",
    "райффайзен": "RAIFFEISEN",
    "райфайзен": "RAIFFEISEN",
    "райф": "RAIFFEISEN",
    "райфф": "RAIFFEISEN",
    "росбанк": "ROSBANK",
    "открытие": "OTKRITIE",
    "почтабанк": "POST BANK",
    "отп": "OTP BANK",
    "совкомбанк": "Sovcombank",
    "совком": "Sovcombank",
    "мтс": "MTS Bank",
    "мтсбанк": "MTS Bank",
    "мтс банк": "MTS Bank",
    "мтс-банк": "MTS Bank",
    "яндекс": "YANDEX BANK",
    "яндексбанк": "YANDEX BANK",
    "yandex": "YANDEX BANK",
    "вб": "Wildberries Bank",
    "вббанк": "Wildberries Bank",
    "wb": "Wildberries Bank",
    "wbбанк": "Wildberries Bank",
    "wildberries": "Wildberries Bank",
    "толчка": "TOCHKA BANK",
    "точка": "TOCHKA BANK",
}


class Superbanking:
    def __init__(self, superbanking_config: SuperbankingConfig) -> None:
        self._superbanking_config = superbanking_config

        with open("./assets/superbanking.json") as f:
            self._superbanking_banks = json.loads(f.read())

        self._bank_name_map: dict[str, str] = {
            bank["bankName"].upper(): bank["nameRus"] for bank in self._superbanking_banks
        }

    def get_bank_name_rus(self, bank_alias: str) -> str | None:
        normalized = re.sub(r"[\s\-]", "", bank_alias.lower())
        bank_name = BANK_ALIASES.get(normalized)
        if bank_name:
            return self._bank_name_map.get(bank_name.upper())
        return None

    def create_payment(self, phone: str, bank_identifier: str, amount: int) -> int:
        return 0
