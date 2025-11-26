# constants
PHOTO_FILE_TYPE = "png"
INSTRUCTION_PHOTOS_DIR = "src/reg_photos/"
SELLER_MENU_TEXT = [
    '⚙️Добавить кабинет', 
    '❌Удалить кабинет',
    'ℹ️Посмотреть кабинеты',
    '⬆️Добавить артикул'
]

MANAGER_NAME = 'Евгения' # в родительном падеже надо
CHANNEL_USERNAME_STR="@viktoriya_cash"  # username канала

OK_WORDS = [
    "ок", "Ок", "спасибо", "Спасибо", "спасибо!", "Спасибо!",
    "хорошо", "Хорошо", "ладно", "окей", "да", "ок.", "ок!",
    "окей!", "Хорошо, сейчас", "понял", "Ладно", "Окэй!"
]
ADMIN_ID_LIST = [694144143, 547299317]


# Wildberries
TIME_SLEEP_API_GET_REMAINS = 3600 #3600*1 # 3600s = 1 hour * 23 = 23 hours

# Aiogram
SKIP_MESSAGE_STATE="skip_msg"

# Telegram
MIN_LEN_TEXT = 12

FIRST_MESSAGE_DELAY_SLEEP =  0.1 #20 #in production 
DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER = 0.2 #5 #in production
TIME_DURATION_BEETWEEN_REMINDER =  60 #3600*12 #in production
TIME_DURATION_BEETWEEN_REMINDER_ORDER_RECEIVE = 60 #3600*23 # in production
TIME_DELTA_CHECK_LAST_USERS_ACTIVITYS = 3600  # in production - every hour check users last time activitys
TIME_DELTA_CHECK_SUB_TO_CHANNEL = 3600*6

BUSINESS_ACCOUNTS_IDS={
    8312986751, # @eugene_saharov
    8239184408, # @viktoria_cashbacks
    8108843318  # @solume_alisa_razdachi (Алиса Раздачи Solume)
}

# reqular expressions for parsing requisites
# 16 numbers or 4 for blocks with 4 numbers with hyphen
card_pattern = r"\b(?:\d{16}|\d{4}(?:[ -]\d{4}){3})\b"

# amount with "р", "руб", "₽"
amount_pattern = (
    r"(?<!\d[ -])"  
    r"\b(\d{1,6}(?:[.,]\d{1,2})?\s?(?:р|руб(?:лей)?|₽|Р|Рублей)?)\b"
    r"(?![ -]?\d)"  
)

# +7910... or 8910... or 7910...
phone_pattern = r"\b(?:\+7|8|7)[\s\-()]?\d{3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}\b"
bank_pattern = (
    r"(?<!\w)("
    r"сбер(?:банк)?|тинькофф|тинькоф|тиньков|т[-\s]?банк|альфа(?:банк)?|"
    r"втб|газпромбанк|райф+айзен|росбанк|открытие|почтабанк|отп|совкомбанк|мтс(?:банк)?|яндекс(?:банк)?"
    r")(?!\w)"
)


# Open AI
GPT_MODEL_NAME='chatgpt-4o-latest'
GPT_MODEL_NAME_PHOTO_ANALYSIS="gpt-5.1"
GPT_MAX_TOKENS=140
GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS=575
GPT_TEMPERATURE=0.75
GPT_REASONING="low" # "low" | "medium" | "high"

# Google Sheets
GOOGLE_SHEETS_TEMPLATE_URL='https://docs.google.com/spreadsheets/d/1KdSieYIl40NmbK8DBCfL2VJNbDFuK_ydJFirnT_XVkY/edit?gid=1585191033#gid=1585191033'
ARTICLES_SHEET_STR="Артикулы"
INSTRUCTION_SHEET_NAME_STR="Инструкция"
BUYERS_SHEET_NAME_STR="Покупатели"

# Redis
NM_IDS_FOR_CASHBACK = [555620866]
REDIS_KEY_SET_TELEGRAM_IDS="TELEGRAM_USERS_IDS" # нужен для проверки новых/старых юзеров, кто писал акку
REDIS_KEY_USER_ROW_POSITION_STRING="USER_ROW_POSITION_IN_GOOGLE_SHEETS" # позиция юзера в гугл-таблице
REDIS_KEY_NM_IDS_REMAINS_HASH="NM_IDS_REMAINS_HASH" # хэш-таблица с количеством остатков каждого артикула из листа "Артикулы"
REDIS_KEY_NM_IDS_ORDERED_LIST="NM_IDS_ORDERED_LIST_FOR_CASHBACK" # упорядоченный список артикулов из листа "Артикулы"
REDIS_KEY_NM_IDS_TITLES_HASH="NM_IDS_NAMES_HASH"