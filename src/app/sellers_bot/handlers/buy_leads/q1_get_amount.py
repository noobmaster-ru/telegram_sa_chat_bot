from decimal import Decimal

from aiogram import  F
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import or_f
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

from src.app.bot.states.seller import SellerStates
from src.app.bot.keyboards.inline import get_yes_no_keyboard
from src.app.bot.keyboards.reply import kb_menu, kb_buy_leads
from src.tools.string_converter_class import StringConverter
from src.infrastructure.db.models import (
    UserORM,
    CabinetORM,
    CashbackTableORM,
    CashbackTableStatus,
    PaymentORM,
    PaymentType,
    PaymentStatus,
    PaymentMethod,
    ServiceType,
)

from src.core.config import constants

from .router import router

# constants.SELLER_MENU_TEXT[1] == "купить лиды"
@router.message(F.text == constants.SELLER_MENU_TEXT[1], or_f(SellerStates.waiting_for_leads, SellerStates.waiting_for_tap_to_menu))
async def start_buy_leads(
    message: Message, 
    state: FSMContext,
    db_session_factory: async_sessionmaker,
):
    telegram_id = message.from_user.id

    async with db_session_factory() as session:
        # Находим юзера
        result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            text = "Пользователь не найден в базе данных. Нажмите /start"
            await message.answer(
                text=StringConverter.escape_markdown_v2(text),
                parse_mode="MarkdownV2"
            )
            return

        # Загружаем кабинеты юзера
        result = await session.execute(
            select(CabinetORM)
            .where(CabinetORM.user_id == user.id)
            .order_by(CabinetORM.created_at)
        )
        cabinets = result.scalars().all()

        if not cabinets:
            text = "У вас пока нет подключённого кабинета и артикула для раздач, нажмите на кнопку *Добавить кабинет*"
            await message.answer(
                text=StringConverter.escape_markdown_v2(text), 
                reply_markup=kb_menu,
                parse_mode="MarkdownV2"
            )
            return
        
    await state.set_state(SellerStates.waiting_for_leads_amount)
    text = f"Сколько лидов хотите купить?\nСейчас цена 1 лида = {constants.PRICE_PER_LEAD} ₽.\n\nВведите число:"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="MarkdownV2"
    )

@router.message(SellerStates.waiting_for_leads)
async def unknown_text(message: Message, state: FSMContext):
    text = f"Пожалуйста, нажмите на кнопку {constants.SELLER_MENU_TEXT[1]}"
    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        reply_markup=kb_buy_leads,
        parse_mode="MarkdownV2"
    )

@router.message(SellerStates.waiting_for_leads_amount)
async def process_leads_amount(
    message: Message,
    state: FSMContext,
    db_session_factory: async_sessionmaker
):
    # 1. Парсим количество лидов
    leads_str = message.text.strip()
    if not leads_str.isdigit():
        text = "Введите количество лидов *числом*, только цифры."
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return
    
    leads = int(leads_str)
    if leads <= 0:
        text = "Введите, пожалуйста, положительное число лидов."
        await message.answer(
            text=StringConverter.escape_markdown_v2(text),
            parse_mode="MarkdownV2"
        )
        return


    total_amount = leads * constants.PRICE_PER_LEAD

    await state.update_data(
        leads_to_buy=leads,
        total_amount=total_amount,
    )

    # 1. находим UserORM по telegram_id
    telegram_id = message.from_user.id
    async with db_session_factory() as session:
        # 2. Находим UserORM по telegram_id
        result = await session.execute(
            select(UserORM).where(UserORM.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            text = "Не удалось найти ваш профиль пользователя.\nПопробуйте начать с /start."
            await message.answer(
                text=StringConverter.escape_markdown_v2(text),
                parse_mode="MarkdownV2"
            )
            return

        # 3. (опционально) определяем кабинет и таблицу кэшбека
        # Если ты где-то в FSM сохраняешь cabinet_id, можно взять оттуда:
        seller_data = await state.get_data()
        cabinet_id = seller_data.get("cabinet_id")

        cashback_table = None
        if cabinet_id is not None:
            result = await session.execute(
                select(CabinetORM)
                .where(CabinetORM.id == cabinet_id)
                .options(
                    # если нужно подтянуть таблицы
                    # selectinload(CabinetORM.cashback_tables)
                )
            )
            cabinet = result.scalar_one_or_none()
            # 2. Находим таблицу кэшбека для кабинета (если cabinet есть)
            cashback_table = None
            if cabinet is not None:
                result = await session.execute(
                    select(CashbackTableORM)
                    .where(CashbackTableORM.cabinet_id == cabinet.id)
                    .order_by(CashbackTableORM.created_at.desc())
                )
                cashback_table = result.scalars().first()

        # 4. Создаём PaymentORM
        payment = PaymentORM(
            user_id=user.id,
            email=user.email,
            cashback_table_id=cashback_table.id if cashback_table else None,
            amount=int(total_amount),  # поле у тебя Integer
            status=PaymentStatus.CREATED,
            payment_method=PaymentMethod.KIRILL_CARD,
            payment_type=PaymentType.REGULAR,
            service_type=ServiceType.CASHBACK,
            service_data={
                "service": "cashback",
                "service_id": cashback_table.id if cashback_table else None,
                "months": None,
                "leads": leads,
                "discounts": [
                    {
                        "discount": None,
                        "description": None,
                        "fix_price": None,
                    }
                ],
                "price_per_lead": constants.PRICE_PER_LEAD,
            },
        )

        session.add(payment)
        await session.commit()
        await session.refresh(payment)

    # сохраняем id платежа в FSM
    await state.update_data(payment_id=payment.id)

    # 5. Сообщение с реквизитами + кнопка "Я оплатил"
    text = (
        f"Вы хотите купить *{leads}* лидов по цене *{constants.PRICE_PER_LEAD} ₽* за лид.\n"
        f"Итого к оплате: *{total_amount} ₽*.\n\n"
        f"Реквизиты для оплаты:\n"
        f"• Карта: `{constants.KIRILL_CARD_NUMBER}` или\n"
        f"• Телефон: `{constants.KIRILL_PHONE_NUMBER}`\n"
        f"• Получатель: *Кирилл К. , Т-банк или Сбер*\n\n"
    )

    await message.answer(
        text=StringConverter.escape_markdown_v2(text),
        parse_mode="MarkdownV2",
        reply_markup=get_yes_no_keyboard(
            callback_prefix="payment",
            statement="оплатил",
        ),
    )
    await state.set_state(SellerStates.waiting_for_payment_confirm_click)