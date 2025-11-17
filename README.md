# telegram_sa_chat_bot
Все константы в src/core/constants.py

Для запуска от селлера нужно(в .env указать пока что):
```    
    - WB_TOKEN
    - GOOGLE_SHEETS_URL (ссылка на гугл-таблицу + вставить туда SERVICE_ACCOUNT_JSON c доступом РЕДАКТОР)
    - NM_IDS_FOR_CASHBACK (указать артикулы для кэшбека)
    - CHANNEL_USERNAME_STR (@nickname канала для раздач)
    - BUSINESS_ACCOUNTS_IDS (множество id бизнес-аккаунтов, нужно, чтобы бот не реагировал на сообщения менеджеров-людей клиентам) 
    - файл result.json с данными по всем перепискам с покупателями от бизнес-аккаунта
    - фотографии артикулов для кэшбека (в src/resources/{nm_id}.png)
```

> VSCodeCounter