from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    # Wildberries
    WB_TOKEN: str


    # Telegram
    TG_BOT_TOKEN: str


    # OpenAI
    OPENAI_TOKEN: str


    # Proxy
    PROXY: str 


    # Google Sheets
    SERVICE_ACCOUNT_JSON: str
    GOOGLE_SHEETS_URL: str


    # Redis
    REDIS_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )