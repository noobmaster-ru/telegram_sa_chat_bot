import logging
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove , CallbackQuery

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.app.bot.states.seller import SellerStates
from src.infrastructure.db.models import CabinetORM
from src.tools.string_converter_class import StringConverter

from .router import router

@router.callback_query(F.data.startswith("select_cabinet_"))
async def process_cabinet_selection(
    callback: CallbackQuery, 
    db_session_factory: async_sessionmaker, 
    state: FSMContext
):
    await callback.answer()
    seller_data = await state.get_data() 
    message_id_to_delete = seller_data["message_id_to_delete"]
    await callback.bot.delete_message(
        chat_id=callback.message.chat.id,
        message_id=message_id_to_delete
    )
    del seller_data['message_id_to_delete']
    await state.set_data(seller_data)
    # 1. Извлекаем ID кабинета из callback_data
    cabinet_id_str = callback.data.split("_")[-1]
    cabinet_id = int(cabinet_id_str)
    
    async with db_session_factory() as session:
        # 2. Получаем объект кабинета из БД, чтобы узнать его название
        cabinet_result = await session.execute(
            select(CabinetORM).where(CabinetORM.id == cabinet_id)
        )
        selected_cabinet = cabinet_result.scalar_one_or_none()
        
        if not selected_cabinet:
            logging.info(" error: cabinet not found")
            text = "Ошибка: Кабинет не найден."
            await callback.answer(
                text=StringConverter.escape_markdown_v2(text),
                show_alert=True,
                parse_mode="MarkdownV2"
            )
            return
        
        # 3. Сохраняем ID кабинета в FSM для дальнейшего использования
        await state.update_data(current_cabinet_id=cabinet_id)

        # 4. Отправляем пользователю подтверждение с НАЗВАНИЕМ
        # show_alert=False (по умолчанию) показывает всплывающее уведомление снизу экрана
        text=f"Выбран кабинет: {selected_cabinet.brand_name}\n\nВведите новый артикул:"
        await callback.message.answer(
            text=StringConverter.escape_markdown_v2(text),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="MarkdownV2"
        )

        
        # 5. Редактируем предыдущее сообщение, чтобы убрать inline-кнопки выбора
        # Например, заменяем кнопки на меню действий внутри кабинета
        # await callback.message.edit_text("Меню кабинета:")
        # await callback.message.edit_reply_markup(reply_markup=kb_cabinet_menu)
        
        # wait for a new nm_id
        await state.set_state(SellerStates.waiting_for_nm_id)
