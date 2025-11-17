from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import quote_plus


class DBSettings(BaseSettings):
    POSTGRESQL_HOST: str
    POSTGRESQL_PORT: int
    POSTGRESQL_USER: str
    POSTGRESQL_PASSWORD: str
    POSTGRESQL_DBNAME: str

    @property
    def DATABASE_URL_asyncpg(self):
        password = quote_plus(self.POSTGRESQL_PASSWORD)
        return f"postgresql+asyncpg://{self.POSTGRESQL_USER}:{password}@{self.POSTGRESQL_HOST}:{self.POSTGRESQL_PORT}/{self.POSTGRESQL_DBNAME}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


db_settings = DBSettings()