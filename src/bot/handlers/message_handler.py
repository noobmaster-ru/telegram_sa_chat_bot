import logging
from aiogram import Router,  types, F
from aiogram.types import Message
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext


from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow


from src.services.open_ai_requests_class import OpenAiRequestClass
from src.services.google_sheets_class import GoogleSheetClass

import redis.asyncio as asyncredis


async def is_known_user(
    redis: asyncredis,
    REDIS_KEY_SET_TELEGRAM_IDS: str,
    user_id: int,
) -> bool:
    """Проверяет, есть ли user_id в Redis."""
    return await redis.sismember(REDIS_KEY_SET_TELEGRAM_IDS, user_id)


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
    instruction_str: str,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    nm_id: str,
    ADMIN_ID_LIST: list,
    client_gpt_5: OpenAiRequestClass
    # FIRST_MESSAGE_LIST: list
):
    telegram_id = message.from_user.id
    text = message.text if message.text else "(без текста)"

    # обновляем время последнего сообщения
    await spreadsheet.update_buyer_last_time_message(telegram_id=telegram_id)

    if "?" in text: 
        # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
        await state.set_state('generating')
        gpt5_response_text = await client_gpt_5.create_gpt_5_response(new_prompt=text)
        await state.set_state(UserFlow.continue_dialog)
        await message.answer(gpt5_response_text)
    else:
        if len(text) > 10:
            await state.set_state('generating')
            gpt5_response_text = await client_gpt_5.create_gpt_5_response(new_prompt=text)
            await state.set_state(UserFlow.continue_dialog)
            await message.answer(gpt5_response_text)    
        elif text in OK_WORDS:
            await message.answer("👍")
        else:
            await message.answer("Напишите, пожалуйста, ваш вопрос более подробнее, одним сообщением")

# здесь надо было business_message указать!!!!!
# первое сообщений пользователя ловит - просто текст
@router.business_message(StateFilter(None))
async def handle_business_message(
    message: Message, 
    state: FSMContext, 
    instruction_str: str,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    nm_id: str,
    ADMIN_ID_LIST: list,
    client_gpt_5: OpenAiRequestClass,
    REDIS_KEY_SET_USERS_ID: str,
    redis: asyncredis
    # FIRST_MESSAGE_LIST: list
):
    telegram_id = message.from_user.id
    username = message.from_user.username or "-"
    full_name = message.from_user.full_name or "-"
    text = message.text if message.text else "-"

    # уже писал нам — пропускаем
    if await is_known_user(redis, REDIS_KEY_SET_USERS_ID, telegram_id):
        return

    # новый пользователь — обрабатываем
    
    # Сохраняем данные пользователя при первом сообщении
    await spreadsheet.add_new_buyer(
        sheet_name=BUYERS_SHEET_NAME,
        username=username,
        telegram_id=telegram_id,
        nm_id=nm_id
    )
    # логируем сообщение
    logging.info(
        f"Первое сообщение от (@{username}, {full_name}), id={telegram_id}: {text} ..."
    )


    # Отправляем инструкцию
    await message.answer(
        instruction_str,
        parse_mode="MarkdownV2",
    )
    # После инструкции — отправляем кнопки "Согласны на условия?"
    await message.answer(
        "Согласны на условия?",
        reply_markup=get_yes_no_keyboard("agree", "согласен(на)")
    )
    # ставим состояние ожидания нажатие на кнопки в поле "Согласны на условия?"
    await state.set_state(UserFlow.waiting_for_agreement)

    
