import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from bot.states.seller import SellerStates
from src.db.models import UserORM

router = Router()

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    telegram_id = message.from_user.id
    username = message.from_user.username if message.from_user.username else "no username"
    first_name = message.from_user.first_name if message.from_user.first_name else "no first_name"
    
    async with db_session_factory() as session:
        # Проверяем, есть ли пользователь
        result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            logging.info(f"user {telegram_id} already in 'users'")
        else:
            # Создаём нового пользователя
            new_user = UserORM(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            session.add(new_user)
            await session.commit()
            logging.info(f"added {telegram_id} into 'users'")

    await message.answer("Здравствуйте! Пришлите,пожалуйста, свой токен от личного кабинета 😊")
    await state.set_state(SellerStates.token_handler)