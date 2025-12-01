import logging
from .router import router
from . import (
    admins_commands, 
    first_message, 
    messages_after_requisites, 
    skip_message
)

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),  # сохраняем в файл
        logging.StreamHandler(),  # выводим в консоль
    ],
)
