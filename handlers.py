from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from database import user_exists, add_user, get_user_count
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

@router.business_message(Command("stats"))
async def cmd_stats(message: Message):
    """Показывает количество пользователей (только администратору)"""
    if message.from_user.id not in ADMIN_ID_LIST:
        await message.answer("⛔ У вас нет прав для этой команды.")
        return

    count = get_user_count()
    await message.answer(f"📊 Всего пользователей написало: *{count}*", parse_mode="MarkdownV2")


@router.message(StateFilter("generating"))
async def wait_response(message: Message):
    await message.answer("Ожидайте ответа, идёт генерация ответа....")

# здесь надо было business_message указать!!!!!
@router.business_message()
async def handle_message(message: Message, state: FSMContext, nm_id: str):
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name or "без full_name"
    text = message.text if message.text else "(без текста)"


    # тест - отвечать могут только я и тема
    if user_id in ADMIN_ID_LIST and not user_exists(user_id):
        add_user(user_id, username)

        # логируем сообщение
        logging.info(
            f"Первое сообщение от (@{username}, full_name), id={user_id}: {text} ..."
        )
        WELCOME_TEXT = (
            "*Здравствуйте\!*\n\n"
            "*Правила выкупа*\n"
            f"1\\. Для заказа необходимо вбить в поисковую строку: `{nm_id}`\n"
            "2\\. Прислать скриншот сделанного заказа\n"
            "3\\. Забрать товар сразу при поступлении в ПВЗ\n\n"

            "*Правила публикации отзыва* \\(за невыполнение одного из пунктов *ВЫПЛАТЫ НЕ БУДЕТ*\\):\n"
            "0\\. Не прикладывать фотографии и видео к отзыву\n"
            "1\\. Оставить *5 звезд* *сразу после получения*\n"
            "2\\. Текст общий формат: \"все понравилось\", \"качество хорошее\"\n"
            "3\\. Разрезать этикетки\n\n"

            "*Правила получения выплаты:*\n"
            "0\\. Прислать скриншот отзыва, разрезанные этикетки, номер телефона и банк для перевода\n"
            "1\\. Отправить нам сообщение: `#выплата_29_сентября`, но с вашей датой\n"
            "2\\. Выплата сразу после публикации отзыва\n\n"

            "*ВАЖНО:*\n"
            "> Во время ВСЕГО ПРОЦЕССА МЫ НЕ БУДЕМ ЧИТАТЬ И ОТВЕЧАТЬ ВАМ\\.\n"
            "> После вашего сообщения с `#выплата_день_месяц` мы проверим корректность выполнения и сразу же отправим платеж\\.\n"
            "> При невыполнении условий мы не отправим вам платеж, пока не будут выполнены все условия\\.\n\n"

            "*Ответы на частые вопросы:*\n"
            "• Предложение актуально, пока товар есть в наличии на ВБ\n"
            "• Отзывов нет, потому что только сегодня начали делать раздачи\n"
            "• Без `#выплата_день_месяц` — выплаты не будет"
        )

        await message.answer(WELCOME_TEXT, parse_mode="MarkdownV2")
    
    # тестируем пока только я и тема
    elif user_id in ADMIN_ID_LIST:
        # переключаем в состояние ожидания(пока ответ от гпт не сформировался)
        await state.set_state('generating')

        try: 
            response = create_response(text)
        except Exception as e:
            await message.answer(f"Произошла ошибка: {e}")
        else:
            await message.answer(response)
        finally:
            await state.clear()
