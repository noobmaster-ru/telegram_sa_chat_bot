import os
from os import environ

from pydantic import BaseModel, Field


class Config(BaseModel):
    postgres_uri: str = Field(alias="POSTGRES_URL")
    redis_uri: str = Field(alias="REDIS_URL")
    json_logs: bool = Field(alias="JSON_LOGS", default=False)
    bot_token: str = Field(alias="BOT_TOKEN")
    service_account_axiomai: str = Field(alias="SERVICE_ACCOUNT_AXIOMAI")
    service_account_axiomai_email: str = Field(alias="SERVICE_ACCOUNT_AXIOMAI_EMAIL")
    openai_api_key: str = Field(alias="OPENAI_TOKEN")

    # MessageDebouncer настройки
    message_debounce_delay: int = Field(alias="MESSAGE_DEBOUNCE_DELAY", default=10)
    message_accumulation_ttl: int = Field(alias="MESSAGE_ACCUMULATION_TTL", default=300)
    immediate_processing_length: int = Field(alias="IMMEDIATE_PROCESSING_LENGTH", default=500)

    # Админы
    admin_telegram_ids: list[int] = Field(
        default_factory=lambda: [int(x) for x in os.getenv("ADMIN_TELEGRAM_IDS", "694144143,547299317").split(",")],
    )
    admin_username: str = Field(alias="ADMIN_USERNAME", default="@noobmaster_rus")


def load_config[ConfigType](
    scope: type[ConfigType] | None = None,
) -> ConfigType | Config:
    if scope:
        return scope(**environ)

    return Config(**environ)
