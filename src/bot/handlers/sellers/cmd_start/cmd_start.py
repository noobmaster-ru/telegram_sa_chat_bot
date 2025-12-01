import logging
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from src.bot.keyboards.reply.menu import kb_menu
from src.db.models import UserORM
from src.bot.states.seller import SellerStates
from src.tools.string_converter_class import StringConverter

from .router import router


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    telegram_id = message.from_user.id
    fullname = message.from_user.full_name 
    user_name = message.from_user.username

    await state.update_data(
        telegram_id=telegram_id,
        fullname=fullname,
        user_name=user_name
    )
    await message.answer(f"Здравствуйте!")
    text = "Давайте зарегистрируем ваши кабинеты, выберите пункт *Добавить кабинет* в меню"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=kb_menu,
        parse_mode="MarkdownV2"
    )
    async with db_session_factory() as session:
        # Проверяем, есть ли пользователь в бд 
        result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        user_exist = result.scalar_one_or_none()
        if not user_exist:
            user = UserORM(
                telegram_id=telegram_id,
                fullname=fullname,
                user_name=user_name
            )
            session.add(user)
            await session.commit()
            logging.info(f"added {telegram_id} into 'users' table")
            
            # session.refresh(user) — подтянет user.id
            await session.refresh(user)   
        
            # Сохраняем user_id в FSM
            await state.update_data(user_id=user.id)
    await state.set_state(SellerStates.waiting_for_tap_to_menu)
