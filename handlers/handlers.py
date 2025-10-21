from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from database import user_exists, add_user
import logging
import re

from generators import create_response
from google_sheets_class import GoogleSheetClass
from handlers.keyboards import get_three_buttons_keyboard, get_different_number_of_buttons_keyboard

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

ADMIN_ID_LIST = [694144143, 547299317]

# список "добрых" слов
OK_WORDS = {"ок", "ok", "хорошо", "ладно", "окей", "да", "ок.", "ок!", "окей!", "хорошо,сейчас", "понял"}


@router.message(StateFilter("generating"))
async def wait_response(message: Message):
    await message.answer("Ожидайте ответа, пожалуйста ...")

# здесь надо было business_message указать!!!!!
@router.business_message()
async def handle_message(
    message: Message, 
    state: FSMContext, 
    instruction_str: str,
    LOWER_LIMIT_OF_MESSAGE_LENGTH: int,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str,
    nm_id: str
):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name or "без full_name"
    text = message.text if message.text else "(без текста)"

    # тест - отвечать могут только я и тема
    if user_id in ADMIN_ID_LIST and not user_exists(user_id):
        add_user(user_id, username)
        
        # Сохраняем данные пользователя при первом сообщении
        spreadsheet.add_new_buyer(
            sheet_name=BUYERS_SHEET_NAME,
            username=username,
            nm_id=nm_id
        )
        # логируем сообщение
        logging.info(
            f"Первое сообщение от (@{username}, {full_name}), id={user_id}: {text} ..."
        )
        # Отправляем инструкцию + кнопки
        await message.answer(
            instruction_str,
            parse_mode="MarkdownV2",
            reply_markup=get_three_buttons_keyboard()
        )
    
    # тестируем пока только я и тема
    elif user_id in ADMIN_ID_LIST:
        
        # обновляем время последнего сообщения
        spreadsheet.update_buyer_last_time_message(
            sheet_name=BUYERS_SHEET_NAME,
            username=username
        )
        # получаем список кнопок, которые ещё не нажаты 
        remaining_buttons = spreadsheet.get_remaining_buttons(
            sheet_name=BUYERS_SHEET_NAME, 
            username=username
        )
        # убираем пробелы и делаем нижний регистр у сообщения
        text = message.text.strip().lower()   
        pattern = r"#выплата_\d{1,2}_[а-яА-ЯёЁ]+"
        if "?" in text: 
            # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
            await state.set_state('generating')
            try: 
                response = create_response(text, instruction_str)
            except Exception as e:
                await message.answer(f"Произошла ошибка: {e}")
            else:
                # если какие-то кнопки ещё не нажал - то к ответу ии кнопки добавятся
                if remaining_buttons:                    
                    await message.answer(
                        response,
                        reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
                    )
                else:
                    await message.answer(response)
            finally:
                await state.clear()
        else:
            if len(text) > LOWER_LIMIT_OF_MESSAGE_LENGTH:
                await state.set_state('generating')
                try: 
                    response = create_response(text, instruction_str)
                except Exception as e:
                    await message.answer(f"Произошла ошибка: {e}")
                else:
                    if remaining_buttons:  
                        await message.answer(
                            response,
                            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
                        )
                    else:
                        await message.answer(response)                
                finally:
                    await state.clear()
            elif text in OK_WORDS:
                await message.answer("👍")
            elif re.fullmatch(pattern, text):
                # текст полностью совпадает с шаблоном #выплата_DD_MONTH
                await message.answer("ВЫПЛАТА_ПРИНИМАЕТСЯ")
                # здесь можно обработать дату и записать в Google Sheet
            elif "#" in text:
                await message.answer(
                    "❌ Вы неправильно указали дату выплаты. "
                    "Исправьте по шаблону, без лишних слов: #выплата_DD_MONTH"
                )
            else:
                await message.answer("Напишите, пожалуйста, ваш вопрос более подробнее, одним сообщением")


# ==== Обработка нажатий на кнопки ====
@router.callback_query(F.data.startswith("feedback_"))
async def handle_feedback(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "feedback_yes" else "Нет"
    
    # обновляем статус "Отзыв оставлен"
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username, 
        button_name="feedback", 
        value=value
    )
    
    # генерируем новые кнопки только для оставшихся
    remaining_buttons = spreadsheet.get_remaining_buttons(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username
    )
    if remaining_buttons:
        await callback.message.answer(
            f"✅ Ваш ответ '{value}' зафиксирован.",
            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
        )
    else:
        await callback.message.answer("✅ Все статусы заполнены, спасибо!")

    await callback.answer()


@router.callback_query(F.data.startswith("order_"))
async def handle_order(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "order_yes" else "Нет"
    
    # обновляем статус "Заказ сделан"
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username, 
        button_name="order", 
        value=value
    )
    
    # генерируем новые кнопки только для оставшихся
    remaining_buttons = spreadsheet.get_remaining_buttons(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username
    )
    if remaining_buttons:
        await callback.message.answer(
            f"✅ Ваш ответ '{value}' зафиксирован.",
            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
        )
    else:
        await callback.message.answer("✅ Все статусы заполнены, спасибо!")

    await callback.answer()


@router.callback_query(F.data.startswith("shk_"))
async def handle_shk(
    callback: CallbackQuery,
    spreadsheet: GoogleSheetClass,
    BUYERS_SHEET_NAME: str
):
    username = callback.from_user.username or "без username"
    value = "Да" if callback.data == "shk_yes" else "Нет"
    
    # обновляем статус "ШК разрезан"
    spreadsheet.update_buyer_button_status(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username, 
        button_name="shk", 
        value=value
    )
    
    # генерируем новые кнопки только для оставшихся
    remaining_buttons = spreadsheet.get_remaining_buttons(
        sheet_name=BUYERS_SHEET_NAME, 
        username=username
    )
    if remaining_buttons:
        await callback.message.answer(
            f"✅ Ваш ответ '{value}' зафиксирован.",
            reply_markup=get_different_number_of_buttons_keyboard(remaining_buttons)
        )
    else:
        await callback.message.answer("✅ Все статусы заполнены, спасибо!")
    await callback.answer()
