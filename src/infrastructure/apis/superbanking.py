import uuid
import logging 
import requests
from src.core.config import settings, constants
from src.tools.string_converter_class import StringConverter
from typing import Optional, Dict


class Superbanking:
    def __init__(self):
        self.api_key = settings.SUPERBANKING_API_KEY
        self.cabinet_id = settings.SUPERBANKING_CABINET_ID
        self.project_id = settings.SUPERBANKING_PROJECT_ID
        self.clearing_center_id = settings.SUPERBANKING_CLEARING_CENTER_ID
        self.pay_number = 0
        self.ALIAS_MAP: Dict[str, str] = {}
        self.BANK_IDENTIFIERS: Dict[str, str] = {}
  
    # Дополнительные короткие АЛИАСЫ, которыми обычно пишут пользователи.
    # Здесь мы биндим алиас → identifier, используя SUPERBANKING_BANKS.
    def _find_by_rus_contains(self, substr: str) -> Optional[str]:
        subs_norm = StringConverter._norm(substr)
        for b in constants.SUPERBANKING_BANKS:
            if subs_norm in StringConverter._norm(b["nameRus"]):
                return b["identifier"]
        return None


    def _find_by_eng_contains(self, substr: str) -> Optional[str]:
        subs_norm = StringConverter._norm(substr)
        for b in constants.SUPERBANKING_BANKS:
            if subs_norm in StringConverter._norm(b["bankName"]):
                return b["identifier"]
        return None
    
    def _add_alias(self, alias: str, *, by_rus: Optional[str] = None, by_eng: Optional[str] = None):
        """
        alias – то, что пишет юзер ('сбер', 'тинькофф', 'т банк', 'ozon', 'wb').
        by_rus/by_eng – кусок официального названия, по которому ищем банк.
        """
        identifier = None
        if by_rus:
            identifier = Superbanking._find_by_rus_contains(self, by_rus)
        if identifier is None and by_eng:
            identifier = Superbanking._find_by_eng_contains(self, by_eng)

        if identifier:
            self.ALIAS_MAP[StringConverter._norm(alias)] = identifier
      
    def create_banks_ids(self):
        for b in constants.SUPERBANKING_BANKS:
            eng = StringConverter._norm(b["bankName"])
            rus = StringConverter._norm(b["nameRus"])
            if eng:
                self.BANK_IDENTIFIERS[eng] = b["identifier"]
            if rus:
                self.BANK_IDENTIFIERS[rus] = b["identifier"]
        # самые популярные варианты, ты можешь дополнять список
        Superbanking._add_alias(self, alias="сбер", by_rus="Сбербанк")
        Superbanking._add_alias(self, alias="сбербанк", by_rus="Сбербанк")
        Superbanking._add_alias(self, alias="сбер банк", by_rus="Сбербанк")
        Superbanking._add_alias(self, alias="сбер-банк", by_rus="Сбербанк")

        Superbanking._add_alias(self, alias="тиньков", by_eng="TINKOFF")
        Superbanking._add_alias(self, alias="тиньк", by_eng="TINKOFF")
        Superbanking._add_alias(self, alias="т банк", by_eng="TINKOFF")
        Superbanking._add_alias(self, alias="тбанк", by_eng="TINKOFF")
        Superbanking._add_alias(self, alias="т-банк", by_eng="TINKOFF")
        Superbanking._add_alias(self, alias="т- банк", by_eng="TINKOFF")
        Superbanking._add_alias(self, alias="т -банк", by_eng="TINKOFF")
        
        Superbanking._add_alias(self, alias="альфа", by_rus="Альфа Банк")
        Superbanking._add_alias(self, alias="альфабанк", by_rus="Альфа Банк")
        Superbanking._add_alias(self, alias="альфа-банк", by_rus="Альфа Банк")

        Superbanking._add_alias(self, alias="втб", by_rus="ВТБ")

        Superbanking._add_alias(self, alias="озон", by_eng="OZON")
        Superbanking._add_alias(self, alias="ozon", by_eng="OZON")

        Superbanking._add_alias(self, alias="райфайзен", by_rus="Райффайзенбанк")
        Superbanking._add_alias(self, alias="райф", by_rus="Райффайзенбанк")
        Superbanking._add_alias(self, alias="райфф", by_rus="Райффайзенбанк")
        Superbanking._add_alias(self, alias="райффайзен", by_rus="Райффайзенбанк")

        Superbanking._add_alias(self, alias="росбанк", by_rus="Росбанк")
        Superbanking._add_alias(self, alias="открытие", by_rus="Открытие")
        Superbanking._add_alias(self, alias="почтабанк", by_rus="Почта Банк")
        Superbanking._add_alias(self, alias="совкомбанк", by_rus="Совкомбанк")
        Superbanking._add_alias(self, alias="мтс банк", by_rus="МТС-Банк")
        Superbanking._add_alias(self, alias="мтсбанк", by_rus="МТС-Банк")
        Superbanking._add_alias(self, alias="мтс-банк", by_rus="МТС-Банк")
        Superbanking._add_alias(self, alias="мтс", by_rus="МТС-Банк")

        Superbanking._add_alias(self, alias="яндекс", by_eng="YANDEX BANK")
        Superbanking._add_alias(self, alias="яндексбанк", by_eng="YANDEX BANK")
        Superbanking._add_alias(self, alias="yandex", by_eng="YANDEX BANK")

        Superbanking._add_alias(self, alias="юмани", by_rus="ЮМани")
        Superbanking._add_alias(self, alias="юmoney", by_eng="YOOMONEY")

        Superbanking._add_alias(self, alias="вббанк", by_eng="Wildberries Bank")
        Superbanking._add_alias(self, alias="вб-банк", by_eng="Wildberries Bank")
        Superbanking._add_alias(self, alias="wbбанк", by_eng="Wildberries Bank")
        Superbanking._add_alias(self, alias="wildberries", by_eng="Wildberries Bank")
        Superbanking._add_alias(self, alias="вб", by_eng="Wildberries Bank")
        Superbanking._add_alias(self, alias="wb", by_eng="Wildberries Bank")

        Superbanking._add_alias(self, alias="толчка", by_eng="TOCHKA BANK")  # если будут писать странно – добавишь свои варианты
        Superbanking._add_alias(self, alias="точка", by_eng="TOCHKA BANK")
        Superbanking._add_alias(self, alias="газпромбанк", by_eng="TOCHKA BANK")
        Superbanking._add_alias(self, alias="псб", by_eng="TOCHKA BANK")


    def parse_bank_identifier(self, text: str) -> Optional[str]:
        """
        Пытается определить identifier банка по произвольному тексту пользователя.

        Логика:
        1) Смотрим на алиасы (сбер, тинькофф, озон, ...).
        2) Если не сработало – пробегаемся по всему списку банков и ищем
            вхождение полного русского/английского названия в тексте.
        """
        t = StringConverter._norm(text)

        # 1. Алиасы
        for alias_norm, identifier in self.ALIAS_MAP.items():
            if alias_norm in t:
                return identifier

        # 2. Полные названия (по списку)
        for b in constants.SUPERBANKING_BANKS:
            if StringConverter._norm(b["nameRus"]) in t or StringConverter._norm(b["bankName"]) in t:
                return b["identifier"]

        return None
    
    def create_payment(
        self,
        phone: str,
        bank_identifier: str,  # <- сразу identifier
        amount: int
    ) -> int:
        url = "https://api.superbanking.ru/cabinet/payout/create?v=1.0.0"
        uid_token = str(uuid.uuid4())
        headers = {
            "x-token-user-api": self.api_key,
            "x-idempotency-token": uid_token, # Генерация уникального ключа идемпотентности
            "Content-Type": "application/json"
            
        }
        payload = {
            "cabinetId": self.cabinet_id,
            "projectId": self.project_id,
            "orderNumber": f"axiomAICashback-{self.pay_number}", # нужно как-то считать все выплаты
            "phone": phone, # "0079876543210"
            "bank": bank_identifier, # "SBER" = 100000000111 , "TINKOFF" = 100000000004
            "amount": amount, 
            "purposePayment": "выплата кэшбека",
            "comment": "выплата кэшбека"
        }
        self.pay_number += 1
        try:
            response = requests.post(url, json=payload, headers=headers)

            response.raise_for_status()            
            if response.status_code == 200:
                resp_json = response.json()
                payment_id = resp_json["data"]["payout"]["id"]
                url = "https://api.superbanking.ru/cabinet/payout/sign?v=1.0.1"
                headers = {
                    "x-token-user-api": self.api_key,
                    "x-idempotency-token": uid_token, # Генерация уникального ключа идемпотентности
                    "Content-Type": "application/json"
                }
                payload = {
                    "cabinetId": self.cabinet_id,
                    "cabinetTransactionId": payment_id,
                }
                try:
                    response = requests.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                except requests.exceptions.HTTPError as http_err:
                    logging.info("HTTP ошибка, sign: %s", http_err)
                    logging.info("Тело ошибки, sign: %s", response.text)
                except Exception as err:
                    logging.info("Произошла ошибка, sign: %s", err)
        except requests.exceptions.HTTPError as http_err:
            logging.info("HTTP ошибка, create: %s", http_err)
            logging.info("Тело ошибки, create: %s", response.text)
        except Exception as err:
            logging.info("Произошла ошибка, create: %s", err)   
        return response.status_code