import os
from os import environ

from pydantic import BaseModel, Field


class SuperbankingConfig(BaseModel):
    api_key: str = Field(alias="SUPERBANKING_API_KEY")
    cabinet_id: str = Field(alias="SUPERBANKING_CABINET_ID")
    project_id: str = Field(alias="SUPERBANKING_PROJECT_ID")
    clearing_center_id: str = Field(alias="SUPERBANKING_CLEARING_CENTER_ID")


class MessageDebouncerConfig(BaseModel):
    message_debounce_delay: int = Field(alias="MESSAGE_DEBOUNCE_DELAY", default=10)
    message_accumulation_ttl: int = Field(alias="MESSAGE_ACCUMULATION_TTL", default=300)
    immediate_processing_length: int = Field(alias="IMMEDIATE_PROCESSING_LENGTH", default=500)


class OpenAIConfig(BaseModel):
    openai_api_key: str = Field(alias="OPENAI_TOKEN")
    proxy: str = Field(alias="PROXY")


class Config(BaseModel):
    postgres_uri: str = Field(alias="POSTGRES_URL")
    redis_uri: str = Field(alias="REDIS_URL")
    json_logs: bool = Field(alias="JSON_LOGS", default=False)
    bot_token: str = Field(alias="BOT_TOKEN")
    service_account_axiomai: str = Field(alias="SERVICE_ACCOUNT_AXIOMAI")
    service_account_axiomai_email: str = Field(alias="SERVICE_ACCOUNT_AXIOMAI_EMAIL")

    admin_telegram_ids: list[int] = Field(
        default_factory=lambda: [int(x) for x in os.getenv("ADMIN_TELEGRAM_IDS", "694144143,547299317").split(",")],
    )
    admin_username: str = Field(alias="ADMIN_USERNAME", default="@noobmaster_rus")

    message_debouncer: MessageDebouncerConfig = Field(default_factory=lambda: MessageDebouncerConfig(**environ))
    superbankink_config: SuperbankingConfig = Field(default_factory=lambda: SuperbankingConfig(**environ))
    openai_config: OpenAIConfig = Field(default_factory=lambda: OpenAIConfig(**environ))


def load_config[ConfigType](
    scope: type[ConfigType] | None = None,
) -> ConfigType | Config:
    if scope:
        return scope(**environ)

    return Config(**environ)
