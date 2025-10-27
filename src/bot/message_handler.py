import logging

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext


from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.bot.states.user_flow import UserFlow


from src.ai_module.open_ai_requests_class import OpenAiRequestClass
from src.google_sheets.google_sheets_class import GoogleSheetClass


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

first_message = []

# список "добрых" слов
OK_WORDS = {"ок", "спасибо", "Спасибо", "ok", "хорошо", "ладно", "окей", "да", "ок.", "ок!", "окей!", "хорошо,сейчас", "понял"}


@router.business_message(StateFilter("generating"))
async def wait_response(message: Message):
    await message.answer("Ожидайте ответа, пожалуйста ...")

# здесь надо было business_message указать!!!!!
# первое сообщений пользователя ловит
@router.business_message(F.text)
async def handle_business_message(
    message: Message, 
    state: FSMContext, 
    instruction_str: str,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    nm_id: str,
    ADMIN_ID_LIST: list,
    client_gpt_5: OpenAiRequestClass
):
    telegram_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name or "без full_name"
    text = message.text if message.text else "(без текста)"


    # тест - отвечать могут только я и тема
    if telegram_id in ADMIN_ID_LIST and not telegram_id in first_message: #and not user_exists(user_id)
        # add_user(user_id, username)
        first_message.append(telegram_id)
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
    # тестируем пока только я и тема
    elif telegram_id in ADMIN_ID_LIST:
        
        # обновляем время последнего сообщения
        await spreadsheet.update_buyer_last_time_message(telegram_id=telegram_id)

        if "?" in text: 
            # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
            await state.set_state('generating')
            try:
                gpt5_response_text = await client_gpt_5.create_gpt_5_response(new_prompt=text)
            except Exception as e:
                await message.answer(f"Произошла ошибка: {e}")
            finally:
                await state.clear()
            await message.answer(gpt5_response_text)
        else:
            if len(text) > 10:
                await state.set_state('generating')
                try: 
                    gpt5_response_text = await client_gpt_5.create_gpt_5_response(new_prompt=text)
                except Exception as e:
                    await message.answer(f"Произошла ошибка: {e}")            
                finally:
                    await state.clear()
                await message.answer(gpt5_response_text)    
            elif text in OK_WORDS:
                await message.answer("👍")
            else:
                await message.answer("Напишите, пожалуйста, ваш вопрос более подробнее, одним сообщением")
