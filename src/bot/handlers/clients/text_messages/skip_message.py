import logging
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.filters import StateFilter

from src.core.config import constants
from .router import router

# need to delete this in next production 
@router.business_message(StateFilter("generating"))
async def wait_response(
    message: Message,
    state: FSMContext
):
    logging.info(f"  user {message.from_user.id} text when we're processing him")
    business_connection_id = message.business_connection_id
    await state.update_data(
        business_connection_id=business_connection_id
    )
    
@router.business_message(StateFilter(constants.SKIP_MESSAGE_STATE))
async def skip_message(
    message: Message,
    state: FSMContext
):
    logging.info(f"  user {message.from_user.id} text when we're processing him")
    business_connection_id = message.business_connection_id
    await state.update_data(
        business_connection_id=business_connection_id
    )