import base64
import io

from aiogram import Bot
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from src.db.models import ArticleORM


async def get_reference_image_data_url_cached(
    db_session_factory: async_sessionmaker[AsyncSession],
    redis: Redis,
    cabinet_id: int,
    nm_id: int,
    seller_bot_token: str
) -> str | None:
    """
    1. Пытается взять эталонное изображение из Redis.
    2. Если нет — берёт photo_file_id из БД, скачивает из Telegram,
       кодирует в base64, кладёт в Redis и возвращает data:image/...;base64,...
    """

    redis_key = f"NM_IDS_REF_IMAGES_FOR_GPT_CLASSIFICATION:{nm_id}"

    # 1. Пробуем взять из Redis
    cached = await redis.get(redis_key)
    if cached:
        return cached.decode("utf-8")

    # 2. Берём photo_file_id из БД - если нет в редис 
    async with db_session_factory() as session:
        stmt = (
            select(ArticleORM.photo_file_id)
            .where(
                ArticleORM.cabinet_id == cabinet_id,
                ArticleORM.article == nm_id,
            )
        )
        result = await session.execute(stmt)
        photo_file_id = result.scalar_one_or_none()

    if not photo_file_id:
        return None

    # 3. Скачиваем файл через seller_bot
    seller_bot = Bot(token=seller_bot_token)

    tg_file = await seller_bot.get_file(photo_file_id)

    buf = io.BytesIO()
    await seller_bot.download_file(tg_file.file_path, destination=buf)
    buf.seek(0)
    image_bytes = buf.read()
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    mime = "image/jpeg"
    if tg_file.file_path and tg_file.file_path.lower().endswith(".png"):
        mime = "image/png"

    data_url = f"data:{mime};base64,{base64_image}"

    # 4. Кладём в Redis , чтобы затем не брать из бд 
    await redis.set(redis_key, data_url)

    return data_url