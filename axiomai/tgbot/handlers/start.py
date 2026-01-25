from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.cabinet import CabinetAlreadyExistsError, BusinessAccountAlreadyLinkedError
from axiomai.application.exceptions.user import UserAlreadyExistsError
from axiomai.application.interactors.create_user import CreateSeller
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.telegram.dialogs.states import CreateCashbackTableStates
from axiomai.infrastructure.telegram.keyboards.reply import kb_add_cabinet, kb_menu
from axiomai.infrastructure.telegram.text import (
    START_MESSAGE_TEXT,
    REGISTRATION_ACCOUNT_WARNING_TEXT,
    ADD_CABINET_INSTRUCTION_TEXT,
)

router = Router()


@router.message(CommandStart())
@inject
async def cmd_start(
    message: Message,
    dialog_manager: DialogManager,
    create_seller: FromDishka[CreateSeller],
    cashback_table_gateway: FromDishka[CashbackTableGateway],
):
    telegram_id = message.from_user.id
    fullname = message.from_user.full_name or "-"
    user_name = message.from_user.username or "-"

    try:
        await create_seller.execute(telegram_id=telegram_id, user_name=user_name, fullname=fullname)
    except BusinessAccountAlreadyLinkedError:
        await message.answer("Кажется, вы с пишите с привязанного бизнес аккаунта, перейдите на рабочий профиль.")
        return
    except CabinetAlreadyExistsError:
        cashback_table = await cashback_table_gateway.get_active_cashback_table_by_telegram_id(telegram_id)
        if not cashback_table:
            await dialog_manager.start(CreateCashbackTableStates.copy_gs_template, mode=StartMode.RESET_STACK)
            return
        await message.answer("Добро пожаловать!", reply_markup=kb_menu)
        return
    except UserAlreadyExistsError:
        pass

    await message.answer(START_MESSAGE_TEXT)
    await message.answer(REGISTRATION_ACCOUNT_WARNING_TEXT)
    await message.answer(ADD_CABINET_INSTRUCTION_TEXT, reply_markup=kb_add_cabinet)
