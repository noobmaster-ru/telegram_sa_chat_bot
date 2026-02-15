import re

# Telegram
WB_CHANNEL_NAME = "@best_wb_hits"

# Superbanking
SUPERBANKING_ORDER_PREFIX = "payment-"
URL_CREATE_PAYMENT = "https://api.superbanking.ru/cabinet/payout/create?v=1.0.0"
URL_SIGN_PAYMENT = "https://api.superbanking.ru/cabinet/payout/sign?v=1.0.1"
TIME_SLEEP_BEFORE_CONFIRM_PAYMENT = 10
URL_CONFIRM_PAYMENT = "https://api.superbanking.ru/cabinet/confirmOperation/createOne?v=1.0.0"
SUPERBANKING_COMMISSION = 25
AXIOMAI_COMMISSION = 5

# Google Sheets
GOOGLE_SHEETS_TEMPLATE_URL = "https://docs.google.com/spreadsheets/d/1KdSieYIl40NmbK8DBCfL2VJNbDFuK_ydJFirnT_XVkY/edit?gid=1585191033#gid=1585191033"

# Платежи
PRICE_PER_LEAD = 20  # ₽/лид
KIRILL_CARD_NUMBER = "5536 9140 2640 7977"
KIRILL_PHONE_NUMBER = "89109681153"

# Регулярки
OK_WORDS = ["Хорошо", "Ок" ,"Ок, хорошо", "Окей", "Ладно", "Понял"]
CARD_PATTERN = re.compile(r"\b(?:\d{16}|\d{4}(?:[ -]\d{4}){3})\b")
BANK_PATTERN = re.compile(
    r"(?<!\w)("
    r"сбер(?:банк)?|тинькофф|тинькоф|тиньков|т[ -]?банк|альфа(?:банк)?|"
    r"втб|озон|газпромбанк|райф+айзен|росбанк|открытие|почтабанк|отп|совкомбанк|мтс(?:банк)?|яндекс(?:банк)?|вб(?:банк)?|wb(?:банк)?"
    r")(?!\w)",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?:\+7|8|7)[\s\-()]?\d{3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}\b")
AMOUNT_PATTERN = re.compile(
    r"(?<!\d[ -])\b(\d{1,6}(?:[.,]\d{1,2})?)\s?(?:р|руб(?:лей)?|₽|Р|Рублей)?\b(?![ -]?\d)", re.IGNORECASE
)
CARD_CLEAN_RE = re.compile(r"[ -]")

# OpenAI API
MODEL_NAME = "gpt-5.1"
GPT_MAX_OUTPUT_TOKENS = 100
GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS = 800
GPT_REASONING = "medium"  # "low" | "medium" | "high"
