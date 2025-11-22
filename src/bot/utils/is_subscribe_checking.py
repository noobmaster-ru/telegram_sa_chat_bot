import asyncio
import time
import json
import logging
from typing import Dict
from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.exceptions import TelegramBadRequest, AiogramError # Импортируем нужные исключения

from src.bot.states.client import ClientStates
from src.core.config import constants
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.core.config import constants
from src.services.google_sheets_class import GoogleSheetClass


# Вспомогательная функция для проверки подписки
async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """
    Проверяет статус подписки пользователя на канал.
    """
    try:
        member = await bot.get_chat_member(
            chat_id=constants.CHANNEL_USERNAME_STR,
            user_id=user_id
        )
        # Пользователь считается подписанным, если его статус 'member', 'administrator' или 'creator'
        if member.status in ["member", "administrator", "creator"]:
            return True
        else:
            return False
    except Exception as e:
        # Обработка возможных ошибок API (например, бот не админ в канале)
        # logging.error(f"Error checking subscription status for user {user_id}: {e}")
        return False

async def google_sheets_sub_updater(
    bot: Bot,
    spreadsheet: GoogleSheetClass
):
    """
    Периодически проверяет подписки всех активных юзеров и обновляет Google Sheets.
    """
    while True:
        try:
            logging.info(f"Starting batch update for users in Google Sheets.")
            telegram_ids_list = await spreadsheet.get_all_telegram_id()
            all_subscription_statuses: Dict[int, bool] = {}

            for telegram_id in telegram_ids_list:
                all_subscription_statuses[telegram_id] = await is_subscribed(bot,telegram_id)
            await spreadsheet.update_subscriptions(all_subscription_statuses)
            logging.info("Finished batch update for Google Sheets.")
        except Exception as e:
            logging.error(f" in inactivity_checker in spreadsheet.update_subscriptions part: {e}")
        # sleep time for a new epoch checking
        await asyncio.sleep(constants.TIME_DELTA_CHECK_SUB_TO_CHANNEL)  