from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from axiomai.infrastructure.database.gateways.cabinet import CabinetGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager
from axiomai.infrastructure.telegram.keyboards.reply import get_kb_menu

router = Router()


@router.message(Command("enable_autopayments"))
@inject
async def enable_autopayments_handler(
    message: Message, cabinet_gateway: FromDishka[CabinetGateway], transaciton_manager: FromDishka[TransactionManager]
) -> None:
    cabinet = await cabinet_gateway.get_cabinet_by_telegram_id_or_business_account_id(message.from_user.id)
    if not cabinet:
        await message.answer("У вас нет привязанного кабинета, пожалуйста, добавьте его через меню.")
        return

    if cabinet.is_superbanking_connect:
        await message.answer("Автовыплаты уже включены.", reply_markup=get_kb_menu(cabinet))
        return

    cabinet.is_superbanking_connect = True
    await transaciton_manager.commit()

    await message.answer("Автовыплаты включены.", reply_markup=get_kb_menu(cabinet))


@router.message(Command("disable_autopayments"))
@inject
async def disable_autopayments_handler(
    message: Message, cabinet_gateway: FromDishka[CabinetGateway], transaciton_manager: FromDishka[TransactionManager]
) -> None:
    cabinet = await cabinet_gateway.get_cabinet_by_telegram_id_or_business_account_id(message.from_user.id)
    if not cabinet:
        await message.answer("У вас нет привязанного кабинета, пожалуйста, добавьте его через меню.")
        return

    if not cabinet.is_superbanking_connect:
        await message.answer("Автовыплаты уже отключены.", reply_markup=get_kb_menu(cabinet))
        return

    cabinet.is_superbanking_connect = False
    await transaciton_manager.commit()

    await message.answer("Автовыплаты отключены.", reply_markup=get_kb_menu(cabinet))
