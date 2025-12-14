# import asyncio
# import logging
# from datetime import datetime, timezone
# from sqlalchemy import select

# from src.infrastructure.db.models import CashbackTableORM
# from src.infrastructure.apis.google_sheets_class import GoogleSheetClass  # твой класс
# from src.core.config import constants

# async def sync_all_cabinets_from_sheets(
#     db_session_factory,
#     gs_api: GoogleSheetClass,
# ):
#     async with db_session_factory() as session:
#         result = await session.execute(select(CashbackTableORM))
#         tables: list[CashbackTableORM] = result.scalars().all()

#     for table in tables:
#         try:
#             nm_id, image_url, article_title, brand_name, instr = (
#                 await gs_api.get_offer_from_settings(table.table_id)
#             )

#             async with db_session_factory() as session:
#                 db_obj = await session.get(CashbackTableORM, table.id)
#                 db_obj.article_nm_id = nm_id
#                 db_obj.article_image_url = image_url
#                 db_obj.article_title = article_title
#                 db_obj.brand_name = brand_name
#                 db_obj.instruction_text = instr
#                 db_obj.last_synced_at = datetime.now(timezone.utc)
#                 await session.commit()
#         except Exception:
#             logging.exception(f"Failed to sync table {table.id}")

# async def periodic_sync_task(db_session_factory, gs_api: GoogleSheetClass):
#     while True:
#         await sync_all_cabinets_from_sheets(db_session_factory, gs_api)
#         await asyncio.sleep(constants.TIME_DELTA_CHECK_GOOGLE_SHEETS_SELLER_DATA_UPDATE)