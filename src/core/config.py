from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Wildberries
    WB_TOKEN_STR: str
    
    # Telegram
    TG_BOT_TOKEN_STR: str
    CHANNEL_USERNAME_STR: str

    # OpenAI
    OPENAI_TOKEN_STR: str
    GPT_MODEL_NAME_STR: str
    GPT_MAX_TOKENS: int
    GPT_TEMPERATURE: float 
    
    # Proxy
    PROXY: str 
    
    # Google Sheets
    SERVICE_ACCOUNT_JSON_STR: str
    GOOGLE_SHEETS_URL_STR: str
    ARTICLES_SHEET_STR: str
    INSTRUCTION_SHEET_NAME_STR: str
    BUYERS_SHEET_NAME_STR: str

    # Redis
    REDIS_URL: str
    REDIS_URL_TEST: str
    REDIS_KEY_SET_TELEGRAM_IDS: str
    REDIS_KEY_USER_ROW_POSITION_STRING: str
    REDIS_KEY_NM_IDS_REMAINS_HASH: str
    REDIS_KEY_NM_IDS_ORDERED_LIST: str
    REDIS_KEY_NM_IDS_TITLES_HASH: str
    
    # Admins
    ADMIN_ID_LIST: list[int] = [694144143, 547299317]

    # constants
    NM_IDS_FOR_CASHBACK: list[int] =  [555620866, 552281618, 518431572]
    TIME_SLEEP_API_GET_REMAINS: int = 21
    OK_WORDS: list[str] = [
        "ок", "Ок", "спасибо", "Спасибо", "спасибо!", "Спасибо!", "хорошо", 
        "Хорошо", "ладно", "окей", "да", "ок.", "ок!", "окей!", "хорошо,сейчас",
        "понял"
    ]
    MIN_LEN_TEXT: int = 12
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8",extra='allow')


settings = Settings()