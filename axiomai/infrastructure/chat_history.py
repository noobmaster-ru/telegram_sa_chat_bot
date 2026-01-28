from datetime import UTC, datetime

from dishka import AsyncContainer

from axiomai.infrastructure.database.gateways.buyer import BuyerGateway
from axiomai.infrastructure.database.transaction_manager import TransactionManager

MAX_CHAT_HISTORY = 10


async def add_to_chat_history(
    di_container: AsyncContainer, buyer_id: int, user_message: str, assistant_response: str
) -> list[dict]:
    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        transaction_manager = await r_container.get(TransactionManager)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        if not buyer:
            return []

        chat_history = list(buyer.chat_history) if buyer.chat_history else []
        chat_history.append(
            {
                "user": user_message,
                "assistant": assistant_response,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        buyer.chat_history = chat_history[-MAX_CHAT_HISTORY:]
        await buyer_gateway.update_buyer(buyer)
        await transaction_manager.commit()
        return buyer.chat_history


async def get_chat_history(di_container: AsyncContainer, buyer_id: int) -> list[dict]:
    async with di_container() as r_container:
        buyer_gateway = await r_container.get(BuyerGateway)
        buyer = await buyer_gateway.get_buyer_by_id(buyer_id)
        return list(buyer.chat_history) if buyer and buyer.chat_history else []
