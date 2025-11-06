import logging
from redis.asyncio import Redis
from aiogram import Router,  types
from aiogram.types import Message
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext


from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow
from src.services.open_ai_requests_class import OpenAiRequestClass
from src.services.google_sheets_class import GoogleSheetClass


router = Router()

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),  # сохраняем в файл
        logging.StreamHandler(),  # выводим в консоль
    ],
)


# список "добрых" слов
OK_WORDS = {"ок","Ок", "спасибо", "Спасибо", "спасибо!", "Спасибо!", "хорошо", "Хорошо", "ладно", "окей", "да", "ок.", "ок!", "окей!", "хорошо,сейчас", "понял"}

# перезапуск бота для админов
@router.business_message(Command('reset'))
async def reset_admin(
    message: types.Message,
    spreadsheet: GoogleSheetClass,
    ADMIN_ID_LIST: list,
    state: FSMContext
):
    telegram_id = message.from_user.id
    if telegram_id in ADMIN_ID_LIST:
        await spreadsheet.delete_row(telegram_id)
        await state.clear()
        await message.answer("bot reseted!")

@router.business_message(StateFilter("generating"))
async def wait_response(message: Message):
    await message.answer("Ожидайте ответа, пожалуйста ...")


@router.business_message(StateFilter(UserFlow.continue_dialog))
async def handle_other_message(
    message: Message, 
    state: FSMContext, 
    spreadsheet: GoogleSheetClass,
    client_gpt_5: OpenAiRequestClass
):
    telegram_id = message.from_user.id
    text = message.text if message.text else "(без текста)"

    user_data = await state.get_data()
    nm_id = user_data.get("nm_id")
    nm_id_amount = user_data.get("nm_id_amount")
    
    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(
        telegram_id=telegram_id,
        is_tap_to_keyboard=False
    )

    if "?" in text: 
        # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
        await state.set_state('generating')
        gpt5_response_text = await client_gpt_5.create_gpt_5_response(
            new_prompt=text,
            nm_id=nm_id,
            count=nm_id_amount
        )
        await state.set_state(UserFlow.continue_dialog)
        await message.answer(gpt5_response_text)
    else:
        if len(text) > 10:
            await state.set_state('generating')
            gpt5_response_text = await client_gpt_5.create_gpt_5_response(
                new_prompt=text,
                nm_id=nm_id,
                count=nm_id_amount
            )
            await state.set_state(UserFlow.continue_dialog)
            await message.answer(gpt5_response_text)    
        elif text in OK_WORDS:
            await message.answer("👍")
        else:
            await message.answer("Напишите, пожалуйста, ваш вопрос более подробнее, одним сообщением")

# здесь надо было business_message указать!!!!!
# первое сообщений пользователя ловит - просто текст
@router.business_message(StateFilter(None))
async def handle_first_message(
    message: Message, 
    state: FSMContext, 
    spreadsheet: GoogleSheetClass,
    INSTRUCTION_SHEET_NAME: str,
    redis: Redis,
    REDIS_KEY_NM_IDS_ORDERED_LIST: str,
    REDIS_KEY_NM_IDS_REMAINS_HASH: str,
    REDIS_KEY_NM_IDS_TITLES_HASH: str
):
    telegram_id = message.from_user.id
    username = message.from_user.username or "-"
    full_name = message.from_user.full_name or "-"
    text = message.text if message.text else "-"

    
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
            await redis.hincrby(REDIS_KEY_NM_IDS_REMAINS_HASH, article, -1) 
            
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
        nm_id_name=product_title
    )
    
    instruction_str = await spreadsheet.get_instruction(
        sheet_instruction=INSTRUCTION_SHEET_NAME, 
        nm_id=available_nm_id, 
        count=nm_id_amount,
        product_title=product_title
    )
    
    # Отправляем инструкцию
    await message.answer(
        text=instruction_str,
        parse_mode="MarkdownV2",
    )
    # После инструкции — отправляем кнопки "Согласны на условия?"
    await message.answer(
        "Согласны на условия?",
        reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
    )
    
    # ставим состояние ожидания нажатие на кнопки в поле "Согласны на условия?"
    await state.set_state(UserFlow.waiting_for_agreement)

    # Сохраняем данные пользователя при первом сообщении
    await spreadsheet.add_new_buyer(
        username=username,
        full_name=full_name,
        telegram_id=telegram_id,
        nm_id=available_nm_id
    )