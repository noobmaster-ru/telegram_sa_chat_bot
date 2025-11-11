import logging
import asyncio
import aiohttp
from redis.asyncio import Redis
import redis.asyncio as asyncredis
from datetime import datetime
from src.core.config import settings, constants

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s"
)
    
class WbApi:
    def __init__(self, token: str, redis: Redis):
        self.token = token
        self.redis = redis

    async def fetch_stocks(
        self,
        session: aiohttp.ClientSession,
        nm_ids: list[int]
    ):
        """
        Запрашивает остатки по заданным параметрам.
        Возвращает JSON-ответ API.
        """
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        now = datetime.now().strftime("%Y-%m-%d")
        payload = {
            "nmIDs": nm_ids,
            "currentPeriod": {
                "start": now,
                "end": now
            },
            "stockType": "",
            "skipDeletedNm": True,
            "orderBy": {
                "field": "stockCount",
                "mode": "desc"
            },
            "availabilityFilters": [
                "deficient", 
                "actual",
                "balanced",
                "nonActual",
                "nonLiquid",
                "invalidData"
            ],
            "offset": 0
        }
        async with session.post(
            url="https://seller-analytics-api.wildberries.ru/api/v2/stocks-report/products/products",
            headers=headers,
            json=payload
        ) as resp:    
            if resp.status == 429:
                logging.warning("[WB API] Too many requests, retrying in 20s...")
                await asyncio.sleep(constants.TIME_SLEEP_API_GET_REMAINS)
                return await self.fetch_stocks(session, nm_ids)
            if resp.status != 200:
                text = await resp.text()
                raise RuntimeError(f"[ERROR] API {resp.status}: {text}")

            data = await resp.json()
            return data

    async def load_nm_ids_and_amounts_to_redis(
        self,
        nm_id_remains_count: dict,
        REDIS_KEY_NM_IDS_REMAINS_HASH: str,
        REDIS_KEY_NM_IDS_TITLES_HASH: str,  
    ) -> None:
        """
        Загружает пары артикул-количество из Google Sheets в Redis с префиксом nm_id_in_articles_sheet
        """
        pipe = self.redis.pipeline(transaction=True)
        for nm_id, data in nm_id_remains_count.items():
            pipe.hset(REDIS_KEY_NM_IDS_REMAINS_HASH, nm_id, data["remains"]) # nm_id: remains 
            pipe.hset(REDIS_KEY_NM_IDS_TITLES_HASH, nm_id, data["nm_id_name"]) # nm_id: name
        await pipe.execute()
        logging.info(f"✅ upload {constants.NM_IDS_FOR_CASHBACK} remains, names into Redis")


async def periodic_task():
    redis = await asyncredis.from_url(settings.REDIS_URL)
    api_client = WbApi(
        token=settings.WB_TOKEN,
        redis=redis
    ) 
    while True:
        result = {}
        try:
            async with aiohttp.ClientSession() as session:
                api_response = await api_client.fetch_stocks(
                    session=session,
                    nm_ids=constants.NM_IDS_FOR_CASHBACK
                )
                data = api_response["data"]
                items = data["items"]
                for item in items:
                    nm_id = item.get("nmID")
                    name = item.get("name")
                    stock_count = item.get("metrics").get("stockCount")

                    result[str(nm_id)] = {  
                        "remains": stock_count,
                        "nm_id_name": name
                    }
                await api_client.load_nm_ids_and_amounts_to_redis(
                    nm_id_remains_count=result,
                    REDIS_KEY_NM_IDS_REMAINS_HASH=constants.REDIS_KEY_NM_IDS_REMAINS_HASH,
                    REDIS_KEY_NM_IDS_TITLES_HASH=constants.REDIS_KEY_NM_IDS_TITLES_HASH
                )            
        except Exception as e:
            logging.error(f" [ERROR] update session: {e}")
        await asyncio.sleep(constants.TIME_SLEEP_API_GET_REMAINS)



async def main():
    await periodic_task()
    
if __name__ == "__main__":
    logging.info(f" Start get_remains.py")
    asyncio.run(main())