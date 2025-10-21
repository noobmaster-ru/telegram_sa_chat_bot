from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from database import user_exists, add_user
import logging

from generators import create_response

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
    LOWER_LIMIT_OF_MESSAGE_LENGTH: int
):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name or "без full_name"
    text = message.text if message.text else "(без текста)"


    # тест - отвечать могут только я и тема
    if user_id in ADMIN_ID_LIST and not user_exists(user_id):
        add_user(user_id, username)

        # логируем сообщение
        logging.info(
            f"Первое сообщение от (@{username}, {full_name}), id={user_id}: {text} ..."
        )
        await message.answer(instruction_str, parse_mode="MarkdownV2")
    
    # тестируем пока только я и тема
    elif user_id in ADMIN_ID_LIST:
        # убираем пробелы и делаем нижний регистр
        text = message.text.strip().lower()   
        if "?" in text: 
            # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
            await state.set_state('generating')
            try: 
                response = create_response(text, instruction_str)
            except Exception as e:
                await message.answer(f"Произошла ошибка: {e}")
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
                    await message.answer(response)
                finally:
                    await state.clear()
            elif text in OK_WORDS:
                await message.answer("👍")
            else:
                await message.answer("Напишите ваш вопрос более подробнее, одним сообщением, пожалуйста.")
