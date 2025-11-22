import asyncio
import time
import json
import logging
from typing import Dict
from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.exceptions import TelegramBadRequest, AiogramError , TelegramForbiddenError# Импортируем нужные исключения

from src.bot.states.client import ClientStates
from src.core.config import constants
from src.bot.keyboards.inline.get_yes_no_keyboard import get_yes_no_keyboard
from src.core.config import constants
from src.services.google_sheets_class import GoogleSheetClass

# 60 - 1 min
# 3600 - 1 hour
# 21600 - 6 hour

TIME_DURATION = constants.TIME_DURATION_BEETWEEN_REMINDER # 1 hour
REMINDER_TIMEOUTS = {
    ClientStates.waiting_for_agreement.state: TIME_DURATION,  
    ClientStates.waiting_for_order.state: TIME_DURATION, 
    
    ClientStates.waiting_for_photo_order.state: TIME_DURATION, 
    ClientStates.waiting_for_order_receive.state: constants.TIME_DURATION_BEETWEEN_REMINDER_ORDER_RECEIVE, # 1 day
    ClientStates.waiting_for_feedback.state: TIME_DURATION, 
    
    
    ClientStates.waiting_for_photo_feedback.state: TIME_DURATION,     
    ClientStates.waiting_for_shk.state: TIME_DURATION,   
    
    
    ClientStates.waiting_for_photo_shk.state: TIME_DURATION,
    ClientStates.waiting_for_requisites.state: TIME_DURATION,         
    
    ClientStates.waiting_for_bank.state: TIME_DURATION,         
    ClientStates.waiting_for_amount.state: TIME_DURATION,  
    ClientStates.waiting_for_card_or_phone_number.state: TIME_DURATION,  
    ClientStates.confirming_requisites.state: TIME_DURATION
}

REMINDER_TEXTS = {
    ClientStates.waiting_for_agreement.state: "Вы в итоге согласны с наши условиями? нажмите, пожалуйста, на кнопку", 
    ClientStates.waiting_for_order.state: "Вы заказали товар? нажмите, пожалуйста, на кнопку", # 24 hour
     
    ClientStates.waiting_for_photo_order.state: "Напоминаю, что ждём скриншот вашего заказа", 
    ClientStates.waiting_for_order_receive.state: "Вы получили товар? (если не получили, проигнорируйте это сообщение, это напоминание🙃)",
    ClientStates.waiting_for_feedback.state: "Вы отзыв оставили 5 звёзд? нажмите , пожалуйста, на кнопку",
    
    
    ClientStates.waiting_for_photo_feedback.state: "Напоминаю, что ждём скриншот вашего отзыва",
    ClientStates.waiting_for_shk.state: "Вы этикетки разрезали? нажмите, пожалуйста, на кнопку ниже",   
    
    ClientStates.waiting_for_photo_shk.state: "Напоминаю, что ждём фото разрезанных этикеток",
    ClientStates.waiting_for_requisites.state: "Пожалуйста, отправьте реквизиты(номер карты/сумму оплаты/банк), чтобы мы могли сделать выплату",
    
    ClientStates.waiting_for_bank.state: "Пожалуйста, отправьте название банка для перевода денег",  
    ClientStates.waiting_for_amount.state: "Пожалуйста, отправьте cумму перевода",  
    ClientStates.waiting_for_card_or_phone_number.state: "Пожалуйста, отправьте номер карты или номер телефона",  
    ClientStates.confirming_requisites.state: "Пожалуйста, подтвердите ваши реквизиты, нажав на кнопку"
}
REPLY_MARKUP_REMIND = [
    ClientStates.waiting_for_agreement.state,
    ClientStates.waiting_for_order.state,
    ClientStates.waiting_for_order_receive.state,
    ClientStates.waiting_for_feedback.state,
    ClientStates.waiting_for_shk.state,
    ClientStates.confirming_requisites.state # сообщение с подтверждением реквизитов не надо удалять!!! там сами реквизиты записаны!!1
]

async def inactivity_checker(
    bot: Bot, 
    storage: RedisStorage
):
    """Периодически проверяет всех пользователей и шлёт напоминания"""
    while True:
        # Сканируем все FSM-ключи
        redis = storage.redis
        async for redis_key in redis.scan_iter(match="fsm:*:*:data"):
            raw_data = await redis.get(redis_key)
            if not raw_data:
                continue
            
            try:
                client_data = json.loads(raw_data.decode())
            except Exception as e:
                logging.warning(f" cant decode data for {redis_key}: {e}")
                continue
            try:
                last_time_activity = client_data["last_time_activity"]   
            except:
                last_time_activity = time.time()
            business_connection_id = client_data["business_connection_id"]
            telegram_id = client_data["telegram_id"] # chat_id == telegram_id
            messages_ids_to_delete = client_data["last_messages_ids"]

            # теперь читаем состояние
            state_key = f"fsm:{telegram_id}:{telegram_id}:state"
            raw_state = await redis.get(state_key)
            state = None
            if raw_state:
                state = raw_state.decode() if isinstance(raw_state, bytes) else raw_state
            else:
                state = None
            
            delta = time.time() - last_time_activity
            if state in REMINDER_TIMEOUTS and delta > REMINDER_TIMEOUTS[state]:
                # отправляем напоминание
                text = REMINDER_TEXTS.get(state)
                msg = None
                if text:
                    if messages_ids_to_delete:
                        
                        # Перебираем все ID по одному
                        for msg_id in messages_ids_to_delete:
                            try:
                                # Используем delete_message для стандартных чатов или delete_business_message для бизнес-чатов
                                if business_connection_id:
                                    await bot.delete_business_messages(
                                        business_connection_id=business_connection_id,
                                        message_ids=[msg_id]
                                    )
                                else:
                                     # Если это обычный чат с ботом
                                    await bot.delete_message(
                                        chat_id=telegram_id,
                                        message_id=msg_id
                                    )

                            except TelegramBadRequest as e:
                                # Это ошибка, которая обычно возникает при превышении 48 часов
                                if "message can't be deleted" in str(e) or "message is too old" in str(e):
                                    logging.warning(f"Message {msg_id} in chat {telegram_id} is too old to delete (48h limit).")
                                else:
                                    logging.error(f"Telegram BadRequest for msg {msg_id}: {e}")
                            
                            except TelegramForbiddenError as e:
                                # Бот не имеет прав удалить сообщение (например, не админ в группе)
                                logging.warning(f"Bot forbidden to delete message {msg_id}: {e}")

                            except Exception as e:
                                logging.error(f"An unexpected error occurred deleting msg {msg_id}: {e}")
                    # try:
                    #     await bot.delete_business_messages(
                    #         business_connection_id=business_connection_id,
                    #         message_ids=messages_ids_to_delete
                    #     )
                    #     # logging.info(f"bot delete messages_ids {messages_ids_to_delete} in dialog with user: {telegram_id}, user state: {state}")
                    # except:
                    #     logging.info(f"bot can't delete messages_ids {messages_ids_to_delete} in dialog with user: {telegram_id}, user state: {state}")
                    if state in REPLY_MARKUP_REMIND:
                        callback_prefix = None
                        statement = None
                        if state == REPLY_MARKUP_REMIND[0]:
                            callback_prefix = "agree"
                            statement = "согласен(на)"
                        elif state == REPLY_MARKUP_REMIND[1]:
                            callback_prefix = "order"
                            statement = "заказал(а)"
                        elif state == REPLY_MARKUP_REMIND[2]:
                            callback_prefix = "receive"  
                            statement = "получил(а)"
                        elif state == REPLY_MARKUP_REMIND[3]:    
                            callback_prefix = "feedback"
                            statement = "оставил(а) отзыв" 
                        elif state == REPLY_MARKUP_REMIND[4]:    
                            callback_prefix = "shk"
                            statement = "разрезал(а) ШК"
                        else: # ClientStates.confirming_requisites.state
                            callback_prefix = "confirm_requisites"
                            statement = "верно" 
                        try:
                            msg = await bot.send_message(
                                chat_id=telegram_id,
                                text=text,
                                business_connection_id=business_connection_id,
                                reply_markup=get_yes_no_keyboard(
                                    callback_prefix=callback_prefix,
                                    statement=statement
                                )
                            )
                            # обновляем таймер, чтобы не спамить
                            new_data = client_data.copy()
                            new_data["last_time_activity"] = time.time()
                            new_data["last_messages_ids"] = [msg.message_id]
                            await redis.set(redis_key, json.dumps(new_data))
                            logging.info(f" send message to user {telegram_id}, in state {state}")
                        except TelegramBadRequest as e:
                            logging.info(f" error in try to send message to user {telegram_id}: {e}")
                            continue
                        except AiogramError as e:
                            logging.info(f" Aiogram error in try to send message to user {telegram_id}: {e}")
                            continue
                        except Exception as e:
                            logging.info(f" unknown error in try to send message to user {telegram_id}: {e}")
                            continue
                    else: # only text need
                        try:
                            msg = await bot.send_message(
                                chat_id=telegram_id,
                                text=text,
                                business_connection_id=business_connection_id
                            )
                            # обновляем таймер, чтобы не спамить
                            new_data = client_data.copy()
                            new_data["last_time_activity"] = time.time()
                            new_data["last_messages_ids"] = [msg.message_id]
                            await redis.set(redis_key, json.dumps(new_data))
                            logging.info(f" send message to user {telegram_id}, in state {state}")
                        except TelegramBadRequest as e:
                            logging.info(f" error in try to send message to user {telegram_id}: {e}")
                            continue
                        except AiogramError as e:
                            logging.info(f" Aiogram error in try to send message to user {telegram_id}: {e}")
                            continue
                        except Exception as e:
                            logging.info(f" unknown error in try to send message to user {telegram_id}: {e}")
                            continue
            else:
                logging.info(f"  client {telegram_id} in {state}, time_delta_last_msg_time_now = {delta:.1f}")
        # sleep time for a new epoch checking
        await asyncio.sleep(constants.TIME_DELTA_CHECK_LAST_USERS_ACTIVITYS)  
