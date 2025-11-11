import asyncio
import time
import json
import logging
from aiogram import Bot
from aiogram.fsm.storage.redis import RedisStorage
from src.bot.states.user_flow import UserFlow
from src.core.config import constants


# 60 - 1 min
# 3600 - 1 hour
# 21600 - 6 hour
TIME_DURATION = constants.TIME_DURATION_BEETWEEN_REMINDER # 21600 
TIME_CHECKING_LAST_USERS_ACTIVITYS = constants.TIME_DELTA_CHECK_LAST_USERS_ACTIVITYS
REMINDER_TIMEOUTS = {
    UserFlow.waiting_for_agreement.state: TIME_DURATION, 
    UserFlow.waiting_for_subcription_to_channel.state: TIME_DURATION, 
    UserFlow.waiting_for_order.state: TIME_DURATION, 
    
    UserFlow.waiting_for_photo_order.state: TIME_DURATION, 
    UserFlow.waiting_for_order_receive.state: TIME_DURATION, 
    UserFlow.waiting_for_feedback.state: TIME_DURATION, 
    
    
    UserFlow.waiting_for_photo_feedback.state: TIME_DURATION,     
    UserFlow.waiting_for_shk.state: TIME_DURATION,   
    
    
    UserFlow.waiting_for_photo_shk.state: TIME_DURATION,
    UserFlow.waiting_for_requisites.state: TIME_DURATION,         
    
    UserFlow.waiting_for_bank.state: TIME_DURATION,         
    UserFlow.waiting_for_amount.state: TIME_DURATION,  
    UserFlow.waiting_for_card_or_phone_number.state: TIME_DURATION,  
    UserFlow.confirming_requisites.state: TIME_DURATION
}

REMINDER_TEXTS = {
    UserFlow.waiting_for_agreement.state: "Вы в итоге согласны с условиями? нажмите на кнопку выше", 
    UserFlow.waiting_for_subcription_to_channel.state: "На канал почему не подписались? без подписки деньги не возвращаем", 
    UserFlow.waiting_for_order.state: "Вы заказали товар? нажмите на кнопку выше", 
     
    UserFlow.waiting_for_photo_order.state: "Напоминаю, что ждём фото вашего заказа",
    UserFlow.waiting_for_order_receive.state: "Товар получили? нажмите на кнопку выше",
    UserFlow.waiting_for_feedback.state: "Здравствуйте! Вы отзыв оставили 5 звёзд?", # 1 мин
    
    
    UserFlow.waiting_for_photo_feedback.state: "Скриншот отзыва отправьте",
    UserFlow.waiting_for_shk.state: "Этикетки разрезали? нажмите на кнопку выше",   
    
    UserFlow.waiting_for_photo_shk.state: "Отправьте фото разрезанных этикеток!!!",
    UserFlow.waiting_for_requisites.state: "Пожалуйста, отправьте реквизиты, чтобы мы могли сделать выплату 💰",
    
    UserFlow.waiting_for_bank.state: "Отправьте название банка!",  
    UserFlow.waiting_for_amount.state: "Отправьте cумму перевода!",  
    UserFlow.waiting_for_card_or_phone_number.state: "Номер карты или номер телефона отправьте",  
    UserFlow.confirming_requisites.state: "Подтвердите реквизиты ваши, на кнопку нажмите выше"
}

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


                # теперь читаем состояние
                state_key = f"fsm:{telegram_id}:{telegram_id}:state"
                raw_state = await redis.get(state_key)
                if raw_state:
                    state = raw_state.decode() if isinstance(raw_state, bytes) else raw_state
                else:
                    state = None
                
                elapsed = time.time() - last_time_activity
                if state in REMINDER_TIMEOUTS and elapsed > REMINDER_TIMEOUTS[state]:
                    # отправляем напоминание
                    text = REMINDER_TEXTS.get(state)
                    if text:
                        logging.info(f"bot send message {telegram_id} in state {state}")
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=text,
                            business_connection_id=business_connection_id
                        )
                        # обновляем таймер, чтобы не спамить
                        new_data = user_data.copy()
                        new_data["last_time_activity"] = time.time()
                        await redis.set(redis_key, json.dumps(new_data))
                else:
                    logging.info(f"  user {telegram_id} in state {state}, elapsed = {elapsed}")
        except Exception as e:
            logging.info(f"[InactivityChecker] Ошибка: {e}")
        await asyncio.sleep(TIME_DURATION)  