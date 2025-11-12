# Wildberries
TIME_SLEEP_API_GET_REMAINS = 21


# Telegram
MIN_LEN_TEXT = 12
CHANNEL_USERNAME_STR="@viktoriya_cash"  # username канала
OK_WORDS = [
    "ок", "Ок", "спасибо", "Спасибо", "спасибо!", "Спасибо!",
    "хорошо", "Хорошо", "ладно", "окей", "да", "ок.", "ок!",
    "окей!", "хорошо,сейчас", "понял"
]
ADMIN_ID_LIST = [694144143, 547299317]
TIME_DURATION_BEETWEEN_REMINDER = 3600 # 3600s = 1 hour  
TIME_DURATION_BEETWEEN_REMINDER_ORDER_RECEIVE = 21600*4 # 21600s = 6 hours * 4 = 1 day
TIME_DELTA_CHECK_LAST_USERS_ACTIVITYS = 600 # 600s = 10 min - every 10 min check users last time activitys
BUSINESS_ACCOUNTS_IDS={
    8312986751, # @eugene_saharov
    8239184408, # @viktoria_cashbacks
}


# Open AI
GPT_MODEL_NAME='chatgpt-4o-latest'
GPT_MODEL_NAME_PHOTO_ANALYSIS="gpt-5"
GPT_MAX_TOKENS=150
GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS=500
GPT_TEMPERATURE=0.6
GPT_REASONING="low" # "low" | "medium" | "high"

# Google Sheets
ARTICLES_SHEET_STR="Артикулы"
INSTRUCTION_SHEET_NAME_STR="Инструкция"
BUYERS_SHEET_NAME_STR="Покупатели"

# Redis
NM_IDS_FOR_CASHBACK = [555620866, 552281618, 518431572]
REDIS_KEY_SET_TELEGRAM_IDS="telegram_users_ids" # нужен для проверки новых/старых юзеров, кто писал акку
REDIS_KEY_USER_ROW_POSITION_STRING="USER_ROW_POSITION_IN_GOOGLE_SHEETS" # позиция юзера в гугл-таблице
REDIS_KEY_NM_IDS_REMAINS_HASH="NM_IDS_REMAINS_HASH" # хэш-таблица с количеством остатков каждого артикула из листа "Артикулы"
REDIS_KEY_NM_IDS_ORDERED_LIST="NM_IDS_ORDERED_LIST_FOR_CASHBACK" # упорядоченный список артикулов из листа "Артикулы"
REDIS_KEY_NM_IDS_TITLES_HASH="NM_IDS_NAMES_HASH"