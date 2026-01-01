from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus

class EnvSettings(BaseSettings):
    # Telegram
    SELLERS_BOT_TOKEN: str
    CLIENTS_BOT_TOKEN: str

    # OpenAI
    OPENAI_TOKEN: str

    # Proxy
    PROXY: str 

    # Google Sheets
    SERVICE_ACCOUNT_AXIOMAI: str
    SERVICE_ACCOUNT_AXIOMAI_EMAIL: str 
    GOOGLE_SHEETS_URL: str

    # Redis
    REDIS_URL: str

    #Superbanking
    SUPERBANKING_API_KEY: str
    SUPERBANKING_CABINET_ID: str
    SUPERBANKING_PROJECT_ID: str
    SUPERBANKING_CLEARING_CENTER_ID: str
    
    # Postgresql
    POSTGRESQL_HOST: str
    POSTGRESQL_PORT: int
    POSTGRESQL_USER: str
    POSTGRESQL_PASSWORD: str
    POSTGRESQL_DBNAME: str
    
    @property
    def DATABASE_URL_asyncpg(self) -> str:
        """URL для async SQLAlchemy (postgresql+asyncpg://...)"""
        password = quote_plus(self.POSTGRESQL_PASSWORD)
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRESQL_USER}:{password}"
            f"@{self.POSTGRESQL_HOST}:{self.POSTGRESQL_PORT}/{self.POSTGRESQL_DBNAME}"
        )

    @property
    def DATABASE_URL_sync(self) -> str:
        """URL для sync SQLAlchemy/Alembic (postgresql://...)"""
        password = quote_plus(self.POSTGRESQL_PASSWORD)
        return (
            f"postgresql://"
            f"{self.POSTGRESQL_USER}:{password}"
            f"@{self.POSTGRESQL_HOST}:{self.POSTGRESQL_PORT}/{self.POSTGRESQL_DBNAME}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )