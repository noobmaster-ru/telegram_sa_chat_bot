import logging
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.methods import ReadBusinessMessage

from src.core.config import constants
from .router import router

# need to delete this in next production 
@router.business_message(StateFilter("generating"))
async def wait_response(message: Message):
    logging.info(f"  user {message.from_user.id} text when we're processing him")
    
    # business_connection_id = message.business_connection_id
    # await message.bot(
    #     ReadBusinessMessage(
    #         business_connection_id=business_connection_id,
    #         chat_id=message.chat.id,
    #         message_id=message.message_id
    #     )
    # )
    
@router.business_message(StateFilter(constants.SKIP_MESSAGE_STATE))
async def skip_message(message: Message):
    logging.info(f"  user {message.from_user.id} text when we're processing him")
    
    # business_connection_id = message.business_connection_id
    # await message.bot(
    #     ReadBusinessMessage(
    #         business_connection_id=business_connection_id,
    #         chat_id=message.chat.id,
    #         message_id=message.message_id
    #     )
    # )
    # await bot.send_chat_action(
    #     chat_id=message.chat.id,
    #     action=ChatAction.TYPING,
    #     business_connection_id = business_connection_id
    # )