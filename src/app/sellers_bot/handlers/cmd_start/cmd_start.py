import logging

from sqlalchemy.ext.asyncio import async_sessionmaker
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from src.app.bot.keyboards.reply import kb_add_cabinet
from src.app.bot.states.seller import SellerStates
from src.infrastructure.db.models import UserORM
from src.tools.string_converter_class import StringConverter
from src.core.config import constants
from .router import router

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    
    telegram_id = message.from_user.id
    fullname = message.from_user.full_name or '-'
    user_name = message.from_user.username or '-'

    
    await state.update_data(
        telegram_id=telegram_id,
        fullname=fullname,
        user_name=user_name
    )
    
    text = (
        "Привет, этот инструмент ускорит в 5-10 раз скорость получения отзывов!\n"
        "А также позволит сократить расходы на ручной труд менеджеров.\n\n\n" 
        "*Стоимость:*\n" 
        "- 20р/лид для первых 5 по счету селлеров\n"
        "- 30р/лид для 6-15 селлеров\n"
        "- 40р/лид для 16-30 селлеров\n\n"
        "30 селлеров - максимальное кол-во селлеров, которые будут одновременно использовать наши услуги.\n"
        "Наша задача - дать неконкурентное преимущество для небольшой группы людей, а не выводить продукт на общий рынок.\n\n"
        "Будущие релизы:\n"
        "- раздача нескольких артикулов последовательно\n"
        "- приоритезация артикулов\n"
        "- автоматические выплаты\n"
        "- раздача одному человеку несколько артикулов параллельно\n\n"
        "*Лид - человек, который написал боту и заинтересовался условиями кэшбека.*\n\n"
        f"P.S. Если что-то непонятно — в любое время нажмите кнопку"
        f"«{constants.SELLER_MENU_TEXT[4]}» или введите команду /support, "
        f"и напишите {constants.ADMIN_USERNAME}."
    )
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )
    async with db_session_factory() as session:
        user = UserORM(
            telegram_id=telegram_id,
            fullname=fullname,
            user_name=user_name,
            email=None
        )
        session.add(user)
        await session.commit()
        logging.info(f"added {telegram_id} into 'users' table")
        
        # session.refresh(user) — подтянет user.id
        await session.refresh(user)   

        # Сохраняем user_id в FSM
        await state.update_data(user_id=user.id)
    # text = "Скиньте ваш email(нужен для связи)"
    text = "Теперь давайте зарегистрируем ваши кабинеты, выберите пункт *Добавить кабинет* в меню"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=kb_add_cabinet,
        parse_mode="MarkdownV2"
    )
    await state.set_state(SellerStates.waiting_for_tap_to_menu)


@router.message(StateFilter(None))
async def admin_texted(message: Message):
    text = "Я буду отправлять вам чеки, нужно будет нажимать на кнопки согласия или не согласия"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2"
    )