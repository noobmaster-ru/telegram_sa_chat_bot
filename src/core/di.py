# src/core/di.py
from dishka import make_async_container, Provider, Scope, provide
from dishka.integrations.aiogram import AiogramProvider

from src.services.google_sheets_class import GoogleSheetClass
from src.services.open_ai_requests_class import OpenAiRequestClass
from src.core.config import settings, constants


        
class ServicesProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_google_sheet(self) -> GoogleSheetClass:
        return GoogleSheetClass(
            service_account_json=settings.SERVICE_ACCOUNT_JSON,
            table_url=settings.GOOGLE_SHEETS_URL,
            buyers_sheet_name=constants.BUYERS_SHEET_NAME_STR,
            REDIS_KEY_USER_ROW_POSITION_STRING=constants.REDIS_KEY_USER_ROW_POSITION_STRING,
            REDIS_KEY_NM_IDS_ORDERED_LIST=constants.REDIS_KEY_NM_IDS_ORDERED_LIST,
            redis_client=None,  # ← Redis мы прокинем через .set_attr() позже
        )

    @provide(scope=Scope.APP)
    async def get_openai(self) -> OpenAiRequestClass:
        return OpenAiRequestClass(
            OPENAI_API_KEY=settings.OPENAI_TOKEN,
            GPT_MODEL_NAME=constants.GPT_MODEL_NAME,
            GPT_MODEL_NAME_PHOTO_ANALYSIS=constants.GPT_MODEL_NAME_PHOTO_ANALYSIS,
            PROXY=settings.PROXY,
            instruction_template=None,  # ← добавим позже
            max_tokens=constants.GPT_MAX_TOKENS,
            max_output_tokens_photo_analysis=constants.GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
            temperature=constants.GPT_TEMPERATURE,
            reasoning=constants.GPT_REASONING
        )


def setup_container():
    return make_async_container(
        ServicesProvider(),
        AiogramProvider()
    )