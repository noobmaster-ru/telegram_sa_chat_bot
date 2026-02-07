from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.application.exceptions.cabinet import BusinessAccountAlreadyLinkedError, CabinetAlreadyExistsError
from axiomai.application.exceptions.user import UserAlreadyExistsError
from axiomai.application.interactors.create_user import CreateSeller
from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.gateways.cashback_table_gateway import CashbackTableGateway
from axiomai.infrastructure.telegram.dialogs.states import CreateCashbackTableStates
from axiomai.infrastructure.telegram.keyboards.reply import get_kb_menu, kb_add_cabinet
from axiomai.infrastructure.telegram.text import (
    ADD_CABINET_INSTRUCTION_TEXT,
    REGISTRATION_ACCOUNT_WARNING_TEXT,
    START_MESSAGE_TEXT,
)

router = Router()


@router.message(CommandStart())
@inject
async def cmd_start(
    message: Message,
    dialog_manager: DialogManager,
    create_seller: FromDishka[CreateSeller],
    cashback_table_gateway: FromDishka[CashbackTableGateway],
    cabinet_gateway: FromDishka[CabinetGateway],
) -> None:
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
            await dialog_manager.start(CreateCashbackTableStates.ask_superbanking, mode=StartMode.RESET_STACK)
            return
        cabinet = await cabinet_gateway.get_cabinet_by_telegram_id(message.from_user.id)
        await message.answer("Добро пожаловать!", reply_markup=get_kb_menu(cabinet))
        return
    except UserAlreadyExistsError:
        pass

    await message.answer(START_MESSAGE_TEXT)
    await message.answer(REGISTRATION_ACCOUNT_WARNING_TEXT)
    await message.answer(ADD_CABINET_INSTRUCTION_TEXT, reply_markup=kb_add_cabinet)
