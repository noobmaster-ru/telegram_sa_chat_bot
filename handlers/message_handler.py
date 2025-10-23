from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext


import logging
import re

from ai_module.generators import create_gpt_5_response
from google_sheets.google_sheets_class import GoogleSheetClass


from handlers.keyboards.get_agreement_keyboard import get_agreement_keyboard

router = Router()

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/bot.log", encoding="utf-8"),  # сохраняем в файл
        logging.StreamHandler(),  # выводим в консоль
    ],
)

# ADMIN_ID_LIST = [694144143, 547299317]
first_message = []
# список "добрых" слов
OK_WORDS = {"ок", "ok", "хорошо", "ладно", "окей", "да", "ок.", "ок!", "окей!", "хорошо,сейчас", "понял"}


@router.message(StateFilter("generating"))
async def wait_response(message: Message):
    await message.answer("Ожидайте ответа, пожалуйста ...")

# здесь надо было business_message указать!!!!!
@router.business_message(F.text)
async def handle_business_message(
    message: Message, 
    state: FSMContext, 
    instruction_str: str,
    LOWER_LIMIT_OF_MESSAGE_LENGTH: int,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    nm_id: str,
    ADMIN_ID_LIST: list
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
        spreadsheet.add_new_buyer(
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
            reply_markup=get_agreement_keyboard()
        )
    # тестируем пока только я и тема
    elif telegram_id in ADMIN_ID_LIST:
        
        # обновляем время последнего сообщения
        spreadsheet.update_buyer_last_time_message(
            sheet_name=BUYERS_SHEET_NAME,
            username=username
        )

        # # убираем пробелы и делаем нижний регистр у сообщения
        # text = message.text.strip().lower()   
        # pattern = r"#выплата_\d{1,2}_[а-яА-ЯёЁ]+"
        if "?" in text: 
            # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
            await state.set_state('generating')
            try: 
                gpt5_response_text = create_gpt_5_response(
                    telegram_id,
                    text, 
                    instruction_str
                )
            except Exception as e:
                await message.answer(f"Произошла ошибка: {e}")
            finally:
                await state.clear()
            await message.answer(gpt5_response_text)
        else:
            if len(text) > LOWER_LIMIT_OF_MESSAGE_LENGTH:
                await state.set_state('generating')
                try: 
                    gpt5_response_text = create_gpt_5_response(
                        telegram_id,
                        text, 
                        instruction_str
                    )
                except Exception as e:
                    await message.answer(f"Произошла ошибка: {e}")            
                finally:
                    await state.clear()
                await message.answer(gpt5_response_text)    
            elif text in OK_WORDS:
                await message.answer("👍")
            # elif re.fullmatch(pattern, text):
            #     # текст полностью совпадает с шаблоном #выплата_DD_MONTH
            #     await message.answer("ВЫПЛАТА_ПРИНИМАЕТСЯ")
            #     # здесь можно обработать дату и записать в Google Sheet
            elif "#" in text:
                await message.answer(
                    "❌ Вы неправильно указали дату выплаты. "
                    "Исправьте по шаблону, без лишних слов: #выплата_DD_MONTH"
                )
            else:
                await message.answer("Напишите, пожалуйста, ваш вопрос более подробнее, одним сообщением")
