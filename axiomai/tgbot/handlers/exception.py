from aiogram import Router, F
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import ErrorEvent, Message
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.cabinet import CabinetNotFoundError

router = Router()


@router.error(ExceptionTypeFilter(CabinetNotFoundError), F.update.message.as_("message"))
@inject
async def cabinet_not_found_handler(event: ErrorEvent, message: Message) -> None:
    await message.answer("❗️ Личный кабинет не найден. Пожалуйста, зарегистрируйтесь. /start")
