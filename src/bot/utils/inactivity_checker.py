import asyncio
import time
import json
import logging
from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage
from src.bot.states.client import ClientStates
from src.core.config import constants
from src.bot.keyboards.get_yes_no_keyboard import get_yes_no_keyboard
from src.core.config import constants

# 60 - 1 min
# 3600 - 1 hour
# 21600 - 6 hour

TIME_DURATION = constants.TIME_DURATION_BEETWEEN_REMINDER # 1 hour
REMINDER_TIMEOUTS = {
    ClientStates.waiting_for_agreement.state: TIME_DURATION, 
    ClientStates.waiting_for_subcription_to_channel.state: TIME_DURATION, 
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
    ClientStates.waiting_for_agreement.state: "Вы в итоге согласны с условиями? нажмите на кнопку", 
    ClientStates.waiting_for_subcription_to_channel.state: "На канал почему не подписались? без подписки деньги не возвращаем. нажмите на кнопку, что подписались", 
    ClientStates.waiting_for_order.state: "Вы заказали товар? нажмите на кнопку", 
     
    ClientStates.waiting_for_photo_order.state: "Напоминаю, что ждём скриншот вашего заказа",
    ClientStates.waiting_for_order_receive.state: "Товар получили? нажмите на кнопку",
    ClientStates.waiting_for_feedback.state: "Вы отзыв оставили 5 звёзд? на кнопку нажмите", # 1 мин
    
    
    ClientStates.waiting_for_photo_feedback.state: "Скриншот отзыва отправьте",
    ClientStates.waiting_for_shk.state: "Этикетки разрезали? нажмите на кнопку",   
    
    ClientStates.waiting_for_photo_shk.state: "Отправьте фото разрезанных этикеток!!!",
    ClientStates.waiting_for_requisites.state: "Пожалуйста, отправьте реквизиты, чтобы мы могли сделать выплату",
    
    ClientStates.waiting_for_bank.state: "Отправьте название банка!",  
    ClientStates.waiting_for_amount.state: "Отправьте cумму перевода!",  
    ClientStates.waiting_for_card_or_phone_number.state: "Номер карты или номер телефона отправьте",  
    ClientStates.confirming_requisites.state: "Подтвердите реквизиты ваши, на кнопку нажмите"
}
REPLY_MARKUP_REMIND = [
    ClientStates.waiting_for_agreement.state,
    ClientStates.waiting_for_subcription_to_channel.state,
    ClientStates.waiting_for_order.state,
    ClientStates.waiting_for_order_receive.state,
    ClientStates.waiting_for_feedback.state,
    ClientStates.waiting_for_shk.state,
    ClientStates.confirming_requisites.state # сообщение с подтверждением реквизитов не надо удалять!!! там сами реквизиты записаны!!1
]
async def inactivity_checker(bot: Bot, storage: RedisStorage):
    """Периодически проверяет всех пользователей и шлёт напоминания"""
    while True:
        try:
            # Сканируем все FSM-ключи
            redis = storage.redis
            async for redis_key in redis.scan_iter(match="fsm:*:*:data"):
                raw_data = await redis.get(redis_key)
                if not raw_data:
                    continue
                
                try:
                    user_data = json.loads(raw_data.decode())
                except Exception as e:
                    logging.warning(f" cant decode data for {redis_key}: {e}")
                    continue
                
                last_time_activity = user_data["last_time_activity"]
                business_connection_id = user_data["business_connection_id"]
                telegram_id = user_data["telegram_id"] # chat_id == telegram_id
                last_messages_ids = user_data["last_messages_ids"]

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
                        logging.info(f"bot delete messages_ids {last_messages_ids} in dialog with user: {telegram_id}, user state: {state}")
                        await bot.delete_business_messages(
                            business_connection_id=business_connection_id,
                            message_ids=last_messages_ids
                        )
                        if state in REPLY_MARKUP_REMIND:
                            callback_prefix = None
                            statement = None
                            if state == REPLY_MARKUP_REMIND[0]:
                                callback_prefix = "agree"
                                statement = "согласен(на)"
                            elif state == REPLY_MARKUP_REMIND[1]:
                                callback_prefix = "subscribe"
                                statement = "подписался(лась)" 
                            elif state == REPLY_MARKUP_REMIND[2]:
                                callback_prefix = "order"
                                statement = "заказал(а)"
                            elif state == REPLY_MARKUP_REMIND[3]:
                                callback_prefix = "receive"  
                                statement = "получил(а)"
                            elif state == REPLY_MARKUP_REMIND[4]:    
                                callback_prefix = "feedback"
                                statement = "оставил(а) отзыв" 
                            elif state == REPLY_MARKUP_REMIND[5]:    
                                callback_prefix = "shk"
                                statement = "разрезал(а) ШК"
                            else: # ClientStates.confirming_requisites.state
                                callback_prefix = "confirm_requisites"
                                statement = "верно"  
                            msg = await bot.send_message(
                                chat_id=telegram_id,
                                text=text,
                                business_connection_id=business_connection_id,
                                reply_markup=get_yes_no_keyboard(
                                    callback_prefix=callback_prefix,
                                    statement=statement
                                )
                            )
                        else: # only text need
                            msg = await bot.send_message(
                                chat_id=telegram_id,
                                text=text,
                                business_connection_id=business_connection_id
                            )
                        # обновляем таймер, чтобы не спамить
                        new_data = user_data.copy()
                        new_data["last_time_activity"] = time.time()
                        new_data["last_messages_ids"] = [msg.message_id]
                        await redis.set(redis_key, json.dumps(new_data))
                else:
                    logging.info(f"  client {telegram_id} in {state}, time_delta_last_msg_time_now = {delta:.1f}")
        except Exception as e:
            logging.info(f"[InactivityChecker] Ошибка: {e}")
        await asyncio.sleep(constants.TIME_DELTA_CHECK_LAST_USERS_ACTIVITYS)  