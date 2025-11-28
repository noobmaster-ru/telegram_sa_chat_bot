import asyncio
import logging
import datetime
from aiogram import Bot
from aiogram.types import Message
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ChatAction
from aiogram.methods import ReadBusinessMessage
from redis.asyncio import Redis


from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.client import ClientStates
from src.apis.google_sheets_class import GoogleSheetClass
from src.bot.utils.last_activity import update_last_activity
from src.core.config import constants
from .router import router


@router.business_message(StateFilter(constants.SKIP_MESSAGE_STATE))
async def skip_message(message: Message, bot: Bot):
    logging.info(f"  user {message.from_user.id} text when we're processing him")
    # business_connection_id = message.business_connection_id
    # await message.bot(
    #     ReadBusinessMessage(
    #         business_connection_id=business_connection_id,
    #         chat_id=message.chat.id,
    #         message_id=message.message_id
    #     )
    # )
    # await bot.send_chat_action(
    #     chat_id=message.chat.id,
    #     action=ChatAction.TYPING,
    #     business_connection_id = business_connection_id
    # )
    # return


# business_message - only for bussines account, handler for first message from clients
@router.business_message(StateFilter(None))
async def handle_first_message(
    message: Message, 
    state: FSMContext, 
    spreadsheet: GoogleSheetClass,
    INSTRUCTION_SHEET_NAME: str,
    redis: Redis,
    REDIS_KEY_NM_IDS_ORDERED_LIST: str,
    REDIS_KEY_NM_IDS_REMAINS_HASH: str,
    REDIS_KEY_NM_IDS_TITLES_HASH: str,
    bot: Bot
):
    await state.set_state(constants.SKIP_MESSAGE_STATE)
    telegram_id = message.from_user.id
    username = message.from_user.username or "-"
    full_name = message.from_user.full_name or "-"
    text = message.text if message.text else "-"
    business_connection_id = message.business_connection_id
    
    # first message from user
    logging.info(
        f"FIRST MESSAGE from (@{username}, {full_name}), id={telegram_id}: {text} ..."
    )
    # === ищем первый артикул, у которого значение > 0 ===
    available_nm_id = None
    nm_id_amount = 0
   
    # Получаем список артикулов в правильном порядке (загрузили в redis в run.py)
    articles = await redis.lrange(REDIS_KEY_NM_IDS_ORDERED_LIST, 0, -1)

    for article in articles:
        # по ключу(артикулу) получаем количество остатков товара в redis
        nm_id_amount = await redis.hget(REDIS_KEY_NM_IDS_REMAINS_HASH, article)
        

        if nm_id_amount and int(nm_id_amount) > 0:
            # уменьшаем на 1 количество остатков артикула
            # await redis.hincrby(REDIS_KEY_NM_IDS_REMAINS_HASH, article, -1) 
            
            # декодируем обратно в строку артикул
            nm_id_decoded = article.decode() if isinstance(article, bytes) else article
            available_nm_id = nm_id_decoded
            
            # по ключу(артикулу) получаем название  товара в redis
            title_bytes = await redis.hget(REDIS_KEY_NM_IDS_TITLES_HASH, article)
            # декодируем обратно в строку
            product_title = title_bytes.decode() if isinstance(title_bytes, bytes) else title_bytes
            # сохраняем количество остатков товара 
            nm_id_amount = int(nm_id_amount)
            break


    if not available_nm_id:
        logging.info(f" all nm_ids are ended ")
        await message.answer("Извините, все товары закончились на складе. Кэшбека не будет.")
        return

    # ========== Сохраняем артикул, остаток товара,название товара в FSM - чтобы для каждого юзера был свой контекст =====
    await state.update_data(
        nm_id=available_nm_id,
        nm_id_amount=nm_id_amount,
        nm_id_name=product_title,
        telegram_id=telegram_id,
        full_name=full_name,
        business_connection_id=business_connection_id,
        last_messages_ids=[]
    )
    
    instruction_str = await spreadsheet.get_instruction(
        sheet_instruction=INSTRUCTION_SHEET_NAME, 
        nm_id=available_nm_id, 
        count=nm_id_amount,
        product_title=product_title
    )
    # Сохраняем данные пользователя при первом сообщении
    await spreadsheet.add_new_buyer(
        username=username,
        full_name=full_name,
        telegram_id=telegram_id,
        nm_id=available_nm_id
    )

    # небольшая задержка
    await asyncio.sleep(constants.FIRST_MESSAGE_DELAY_SLEEP)
    
    # Сначала помечаем сообщение как прочитанное
    await message.bot(
        ReadBusinessMessage(
            business_connection_id=business_connection_id,
            chat_id=message.chat.id,
            message_id=message.message_id
        )
    )
    
    # небольшая задержка
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    # показываем "печатает"
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await message.answer(text="Здравствуйте!")
    
    
    # =========
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await message.answer(
        text="Сейчас пришлю вам мою подробную инструкцию, пожалуйста, выполняйте все условия!! Вам также будет помогать мой робот-помощник🤖, вы не пугайтесь😂 , он поможет быстрее собрать все нужные данные, реквизиты, затем я их проверю и пришлю вам деньги ☺️. "
    )
    
    
    # =========
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    await message.answer(text="Вот инструкция")
    
    await bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.TYPING,
        business_connection_id = business_connection_id
    )
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    # Отправляем инструкцию
    await message.answer(
        text=instruction_str,
        parse_mode="MarkdownV2",
    )
    
    await asyncio.sleep(constants.DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER)
    # Отправляем бота! и отправляем кнопки "Согласны на условия?"
    msg = await message.answer(
        f"Здравствуйте! Я - 🤖-помощник {constants.MANAGER_NAME}.\nВы согласны на наши условия кэшбека?",
        reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
    )
    # ставим состояние ожидания нажатие на кнопки в поле "Согласны на условия?"
    await state.set_state(ClientStates.waiting_for_agreement)
    await update_last_activity(state, msg)