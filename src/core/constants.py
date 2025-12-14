# constants
INSTRUCTION_PHOTOS_DIR = "src/reg_photos/"
PRICE_PER_LEAD = 20  # руб/лид — пока константой
KIRILL_CARD_NUMBER = "5536 9140 2640 7977"
KIRILL_PHONE_NUMBER = "89109681153"

# Telegram
ADMIN_ID_LIST = [694144143, 547299317]
ADMIN_USERNAME = "@noobmaster_rus"
SKIP_MESSAGE_STATE="skip_msg"
CLIENTS_BOT_USERNAME = "@axiomAI_business_test2_bot" #  "@testing_ai_cashback_bot" 
SELLERS_BOT_USERNAME = "@axiomAI_test2_bot" #   "@axiom_agi_bot" 
BOT_TO_GET_ID = "@username_to_id_bot"
SELLER_MENU_TEXT = [
    '⚙️Добавить кабинет', # 0
    '💰Купить лиды', # 1, constants.SELLER_MENU_TEXT[1]
    'ℹ️Мой кабинет', # 2, редирект на сообщение с кабинетом
    '⬆️Мой артикул', # 3, редирект на сообщение с артикулом
    "🆘 Поддержка", # 4 поддержка
    "Пропустить result.json", # 5 skip result.json
]

OK_WORDS = [
    "ок", "Ок", "спасибо", "Спасибо", "спасибо!", "Спасибо!",
    "хорошо", "Хорошо", "ладно", "окей", "да", "ок.", "ок!",
    "окей!", "Хорошо, сейчас", "понял", "Ладно", "Окэй!"
]
MIN_LEN_TEXT = 12
FIRST_MESSAGE_DELAY_SLEEP = 60 #  in production 
DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER = 5 #in production
TIME_DURATION_BEETWEEN_REMINDER =  3600*23 #in production
TIME_DURATION_BEETWEEN_REMINDER_ORDER_RECEIVE =  3600*23 #in production
TIME_DELTA_CHECK_LAST_USERS_ACTIVITYS = 3600  #  in production - every hour check users last time activitys


# REGULAR EXPRESSIONS
# 16 numbers or 4 for blocks with 4 numbers with hyphen
card_pattern = r"\b(?:\d{16}|\d{4}(?:[ -]\d{4}){3})\b"

# amount with "р", "руб", "₽"
amount_pattern = (
    r"(?<!\d[ -])"  
    r"\b(\d{1,6}(?:[.,]\d{1,2})?\s?(?:р|руб(?:лей)?|₽|Р|Рублей)?)\b"
    r"(?![ -]?\d)"  
)

# +7910... or 8910... or 7910...
phone_pattern = r"(?:\+7|8|7)[\s\-()]?\d{3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}\b"
bank_pattern = (
    r"(?<!\w)("
    r"сбер(?:банк)?|тинькофф|тинькоф|тиньков|т[ -]?банк|альфа(?:банк)?|"
    r"втб|озон|газпромбанк|райф+айзен|росбанк|открытие|почтабанк|отп|совкомбанк|мтс(?:банк)?|яндекс(?:банк)?|вб(?:банк)?|wb(?:банк)?"
    r")(?!\w)"
)


# Open AI
GPT_MODEL_NAME='chatgpt-4o-latest'
GPT_MODEL_NAME_PHOTO_ANALYSIS="gpt-5.1"
GPT_MAX_TOKENS=300
GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS=850
GPT_TEMPERATURE=1.45
GPT_REASONING="medium" # "low" | "medium" | "high"

# Google Sheets
CABINET_CONTEXT_TTL_SECONDS = 120
GOOGLE_SHEETS_TEMPLATE_URL='https://docs.google.com/spreadsheets/d/1KdSieYIl40NmbK8DBCfL2VJNbDFuK_ydJFirnT_XVkY/edit?gid=1585191033#gid=1585191033'
SETTINGS_SHEET_NAME_STR="Настройка"
BUYERS_SHEET_NAME_STR="Покупатели"
INSTRUCTION_CELL = "H2"
INSTRUCTION_CELL_TEMPLATE = "A2"

TIME_UPDATE_CELL = "B5"
TIME_UPDATE_CELL_UPPER = "B4"
TIME_DELTA_CHECK_GOOGLE_SHEETS_SELLER_DATA_UPDATE = 300 # 5 минут

LEADS_REMAIN_CELL = "A5"
LEADS_REMAIN_CELL_UPPER = "A4"
TIME_DELTA_CHECK_LEADS_REMAIN = 3600 * 12 # 12 часов 

# Redis
REDIS_KEY_BUSINESS_ACCOUNTS_IDS = "BUSINESS_ACCOUNTS_IDS_TO_SKIP_MESSAGES_FROM_MANAGERS"
REDIS_KEY_USER_ROW_POSITION_STRING="USER_ROW_POSITION_IN_GOOGLE_SHEETS" # позиция юзера в гугл-таблице
REDIS_KEY_NM_IDS_IMAGES = "NM_IDS_REF_IMAGES_FOR_GPT_CLASSIFICATION"
REDIS_KEY_LEADS_USED = "LEADS_USED"
REDIS_KEY_OLD_USERS = "OLD_USERS"