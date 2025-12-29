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


alembic:
```
    alembic revision --autogenerate -m "..."
    alembic upgrade head

    на тесте:
    docker compose run --rm clients_bot uv run python -m alembic upgrade head
```

очистка таблиц - для теста
```
    TRUNCATE TABLE
        payments,
        cashback_tables,
        articles,
        cabinets,
        users
    RESTART IDENTITY CASCADE;
```
> VSCodeCounter

docker compose run --rm clients_bot uv run python -m alembic revision -m "..." 
Полностью сбросить локальную БД и начать с нуля:
```
    docker compose down
    rm -rf pgdata_dev
    docker compose up -d --build
    docker compose run --rm clients_bot uv run python -m alembic upgrade head
    docker compose logs -f
```