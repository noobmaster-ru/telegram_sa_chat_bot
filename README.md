# telegram_sa_chat_bot
Все константы в src/core/constants.py

В Redis сохраняются два вида состояний:
```
    Для клиентов-покупателей: 
        fsm:{clients_bot_id}:{bussiness_connection_id}:{telegram_id}:{telegram_id}:[state/data]
    то есть разделяем сначала по clients_bot_id , потом по bus_conn (для каждого акка будет свой), затем уже по юзерам
    
    Для селлеров-покупателей:
        fsm:{seller_bot_id}:{telegram_id}:{telegram_id}:[data/state]
    
    то есть разделяем сначала по seller_bot_id, затем по юзерам
```

Для запуска от селлера нужно(в .env указать пока что):
```    
    - GOOGLE_SHEETS_URL (ссылка на гугл-таблицу + вставить туда SERVICE_ACCOUNT_JSON c доступом РЕДАКТОР)
    - NM_IDS_FOR_CASHBACK (указать артикулы для кэшбека)
    - BUSINESS_ACCOUNTS_IDS (множество id бизнес-аккаунтов, нужно, чтобы бот не реагировал на сообщения менеджеров-людей клиентам) 
    - фотографии артикулов для кэшбека (в src/resources/{nm_id}.png)
```

alembic:
```
    alembic revision --autogenerate -m "..."
    alembic upgrade head
```
> VSCodeCounter