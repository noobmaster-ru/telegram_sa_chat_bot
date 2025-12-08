from aiogram.filters import BaseFilter
from aiogram.types import Message


class ImageDocument(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        doc = message.document
        return bool(
            doc
            and doc.mime_type
            and doc.mime_type.startswith("image/")
        )