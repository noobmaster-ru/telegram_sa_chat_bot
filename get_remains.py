import asyncio
import aiohttp
from redis.asyncio import Redis
import redis.asyncio as asyncredis
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import json 

async def fetch_stocks(
    wb_token: str,
    session: aiohttp.ClientSession,
    nm_ids: list
):
    """
    Запрашивает остатки по заданным параметрам.
    Возвращает JSON-ответ API.
    """
    headers = {
        "Authorization": wb_token,
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
            await asyncio.sleep(20)
            return await fetch_stocks(wb_token, session, nm_ids)
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Ошибка API {resp.status}: {text}")

        data = await resp.json()
        return data



async def load_nm_ids_and_amounts_to_redis(
    redis_client: Redis,
    nm_id_remains_count: dict,
    REDIS_KEY_NM_IDS_REMAINS_HASH: str,
    REDIS_KEY_NM_IDS_TITLES_HASH: str,  
) -> None:
    """
    Загружает пары артикул-количество из Google Sheets в Redis с префиксом nm_id_in_articles_sheet
    """

    # Пропускаем заголовок
    pipe = redis_client.pipeline(transaction=True)


    for nm_id, data in nm_id_remains_count.items():
        # сохраняем количество в хэш: nm_id=amount 
        pipe.hset(REDIS_KEY_NM_IDS_REMAINS_HASH, nm_id, data["remains"])
        # сохраняем название в хэш: nm_id=title 
        pipe.hset(REDIS_KEY_NM_IDS_TITLES_HASH, nm_id, data["nm_id_name"])

    await pipe.execute()


    logging.info(f"✅ Put {len(nm_id_remains_count)-1} nm_ids into Redis DB")
    
async def main():
    load_dotenv()
    WB_TOKEN_STR = os.getenv("WB_TOKEN_STR")
    REDIS_URL = os.getenv("REDIS_URL_TEST")
    REDIS_KEY_NM_IDS_REMAINS_HASH = os.getenv("REDIS_KEY_NM_IDS_REMAINS_HASH")
    REDIS_KEY_NM_IDS_TITLES_HASH = os.getenv("REDIS_KEY_NM_IDS_TITLES_HASH")
    
    redis = await asyncredis.from_url(REDIS_URL)
    
    nm_ids = [508040605]  # ← подставьте ваши nmIDs
    
    result = {}
    async with aiohttp.ClientSession() as session:
        try:
            api_response = await fetch_stocks(
                wb_token=WB_TOKEN_STR,
                session=session,
                nm_ids=nm_ids
            )
            data = api_response["data"]
            items = data["items"]
            for item in items:
                nm_id = item.get("nmID")
                name = item.get("name")
                stock_count = item.get("metrics").get("stockCount")

                result[str(nm_id)] = {  # приводим ключ к строке!
                    "remains": stock_count,
                    "nm_id_name": name
                }
            # print(result)
            await load_nm_ids_and_amounts_to_redis(
                redis,
                result,
                REDIS_KEY_NM_IDS_REMAINS_HASH,
                REDIS_KEY_NM_IDS_TITLES_HASH
            )

            with open("data_statistics_per_nm_id.json", mode="w",encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print("Произошла ошибка:", e)

if __name__ == "__main__":
    asyncio.run(main())