import re
from typing import  List, Dict

# constants
INSTRUCTION_PHOTOS_DIR = "src/reg_photos/"
PRICE_PER_LEAD = 20  # руб/лид — пока константой
KIRILL_CARD_NUMBER = "5536 9140 2640 7977"
KIRILL_PHONE_NUMBER = "89109681153"

# Telegram
ADMIN_ID_LIST = [694144143, 547299317]
ADMIN_USERNAME = "@noobmaster_rus"
SKIP_MESSAGE_STATE="skip_msg"
CLIENTS_BOT_USERNAME = "@axiomai_develop_business_bot"
SELLERS_BOT_USERNAME = "@axiomai_develop_bot"

# CLIENTS_BOT_USERNAME = "@axiomAI_business_test2_bot" #  "@testing_ai_cashback_bot" 
# SELLERS_BOT_USERNAME = "@axiomAI_test2_bot" #   "@axiom_agi_bot" 

BOT_TO_GET_ID = "@username_to_id_bot"
SELLER_MENU_TEXT = [
    '⚙️Добавить кабинет', # 0
    '💰Купить лиды', # 1, constants.SELLER_MENU_TEXT[1]
    'ℹ️Мой кабинет', # 2, редирект на сообщение с кабинетом
    '⬆️Мой артикул', # 3, редирект на сообщение с артикулом
    "🆘 Поддержка", # 4 поддержка
    "Пропустить result.json", # 5 skip result.json
]

OK_WORDS = [
    "ок", "Ок", "спасибо", "Спасибо", "спасибо!", "Спасибо!",
    "хорошо", "Хорошо", "ладно", "окей", "да", "ок.", "ок!",
    "окей!", "Хорошо, сейчас", "понял", "Ладно", "Окэй!"
]
MIN_LEN_TEXT = 12
FIRST_MESSAGE_DELAY_SLEEP = 60 #  in production 
DELAY_BEETWEEN_BOT_MESSAGES_IN_FIRST_HANDLER = 5 #in production
TIME_DURATION_BEETWEEN_REMINDER =  3600*23 #in production
TIME_DURATION_BEETWEEN_REMINDER_ORDER_RECEIVE =  3600*23 #in production
TIME_DELTA_CHECK_LAST_USERS_ACTIVITYS = 3600  #  in production - every hour check users last time activitys


# REGULAR EXPRESSIONS
# 16 numbers or 4 for blocks with 4 numbers with hyphen
card_pattern = r"\b(?:\d{16}|\d{4}(?:[ -]\d{4}){3})\b"

# amount with "р", "руб", "₽"
amount_pattern = (
    r"(?<!\d[ -])"  
    r"\b(\d{1,6}(?:[.,]\d{1,2})?\s?(?:р|руб(?:лей)?|₽|Р|Рублей)?)\b"
    r"(?![ -]?\d)"  
)


bank_pattern = (
    r"(?<!\w)("
    r"сбер(?:банк)?|тинькофф|тинькоф|тиньков|т[ -]?банк|альфа(?:банк)?|"
    r"втб|озон|газпромбанк|райф+айзен|росбанк|открытие|почтабанк|отп|совкомбанк|мтс(?:банк)?|яндекс(?:банк)?|вб(?:банк)?|wb(?:банк)?"
    r")(?!\w)"
)
# +7910... or 8910... or 7910...
phone_pattern = r"(?:\+7|8|7)[\s\-()]?\d{3}[\s\-()]?\d{3}[\s\-()]?\d{2}[\s\-()]?\d{2}\b"


# Open AI
GPT_MODEL_NAME='chatgpt-4o-latest'
GPT_MODEL_NAME_PHOTO_ANALYSIS="gpt-5.1"
GPT_MAX_TOKENS=300
GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS=850
GPT_TEMPERATURE=1.45
GPT_REASONING="medium" # "low" | "medium" | "high"

# Google Sheets
CABINET_CONTEXT_TTL_SECONDS = 120
GOOGLE_SHEETS_TEMPLATE_URL='https://docs.google.com/spreadsheets/d/1KdSieYIl40NmbK8DBCfL2VJNbDFuK_ydJFirnT_XVkY/edit?gid=1585191033#gid=1585191033'
SETTINGS_SHEET_NAME_STR="Настройка"
BUYERS_SHEET_NAME_STR="Покупатели"
INSTRUCTION_CELL = "H2"
INSTRUCTION_CELL_TEMPLATE = "A2"

TIME_UPDATE_CELL = "B5"
TIME_UPDATE_CELL_UPPER = "B4"
TIME_DELTA_CHECK_GOOGLE_SHEETS_SELLER_DATA_UPDATE = 300 # 5 минут

LEADS_REMAIN_CELL = "A5"
LEADS_REMAIN_CELL_UPPER = "A4"
TIME_DELTA_CHECK_LEADS_REMAIN = 3600 * 12 # 12 часов 

# Redis
REDIS_KEY_BUSINESS_ACCOUNTS_IDS = "BUSINESS_ACCOUNTS_IDS_TO_SKIP_MESSAGES_FROM_MANAGERS"
REDIS_KEY_USER_ROW_POSITION_STRING="USER_ROW_POSITION_IN_GOOGLE_SHEETS" # позиция юзера в гугл-таблице
REDIS_KEY_NM_IDS_IMAGES = "NM_IDS_REF_IMAGES_FOR_GPT_CLASSIFICATION"
REDIS_KEY_LEADS_USED = "LEADS_USED"
REDIS_KEY_OLD_USERS = "OLD_USERS"


SUPERBANKING_BANKS: List[Dict[str, str]] = [
    {
      "bankName": "Gazprombank",
      "identifier": "100000000001",
      "nameRus": "Газпромбанк"
    },
    {
      "bankName": "SKB-bank",
      "identifier": "100000000003",
      "nameRus": "СКБ-банк"
    },
    {
      "bankName": "TINKOFF",
      "identifier": "100000000004",
      "nameRus": "T-Банк"
    },
    {
      "bankName": "VTB",
      "identifier": "100000000005",
      "nameRus": "ВТБ"
    },
    {
      "bankName": "AK BARS BANK",
      "identifier": "100000000006",
      "nameRus": "Ак Барс Банк"
    },
    {
      "bankName": "RAIFFEISEN",
      "identifier": "100000000007",
      "nameRus": "Райффайзенбанк"
    },
    {
      "bankName": "ALFA",
      "identifier": "100000000008",
      "nameRus": "Альфа Банк"
    },
    {
      "bankName": "Promsvyazbank",
      "identifier": "100000000010",
      "nameRus": "Промсвязьбанк"
    },
    {
      "bankName": "RNCB",
      "identifier": "100000000011",
      "nameRus": "РНКБ Банк"
    },
    {
      "bankName": "ROSBANK",
      "identifier": "100000000012",
      "nameRus": "Росбанк"
    },
    {
      "bankName": "Sovcombank",
      "identifier": "100000000013",
      "nameRus": "Совкомбанк"
    },
    {
      "bankName": "RUSSIAN STANDARD",
      "identifier": "100000000014",
      "nameRus": "Банк Русский Стандарт"
    },
    {
      "bankName": "OTKRITIE",
      "identifier": "100000000015",
      "nameRus": "Банк ФК Открытие"
    },
    {
      "bankName": "POST BANK",
      "identifier": "100000000016",
      "nameRus": "Почта Банк"
    },
    {
      "bankName": "MTS Bank",
      "identifier": "100000000017",
      "nameRus": "МТС-Банк"
    },
    {
      "bankName": "OTP BANK",
      "identifier": "100000000018",
      "nameRus": "ОТП Банк"
    },
    {
      "bankName": "ROSSELKHOZBANK",
      "identifier": "100000000020",
      "nameRus": "Россельхозбанк"
    },
    {
      "bankName": "YOOMONEY",
      "identifier": "100000000022",
      "nameRus": "ЮМани"
    },
    {
      "bankName": "HOME CREDIT BANK",
      "identifier": "100000000024",
      "nameRus": "Хоум Кредит Банк"
    },
    {
      "bankName": "CREDIT BANK OF MOSCOW",
      "identifier": "100000000025",
      "nameRus": "Московский Кредитный Банк"
    },
    {
      "bankName": "BANK URALSIB",
      "identifier": "100000000026",
      "nameRus": "БАНК УРАЛСИБ"
    },
    {
      "bankName": "CREDIT EUROPE BANK",
      "identifier": "100000000027",
      "nameRus": "Кредит Европа Банк (Россия)"
    },
    {
      "bankName": "AVANGARD",
      "identifier": "100000000028",
      "nameRus": "Банк АВАНГАРД"
    },
    {
      "bankName": "Bank Saint-Petersburg",
      "identifier": "100000000029",
      "nameRus": "Банк Санкт-Петербург"
    },
    {
      "bankName": "UniCredit Bank",
      "identifier": "100000000030",
      "nameRus": "ЮниКредит Банк"
    },
    {
      "bankName": "UBRR",
      "identifier": "100000000031",
      "nameRus": "УБРиР"
    },
    {
      "bankName": "RENAISSANCE CREDIT",
      "identifier": "100000000032",
      "nameRus": "Ренессанс Кредит"
    },
    {
      "bankName": "Promsvyazbank(B2P)",
      "identifier": "100000000033",
      "nameRus": "Промсвязьбанк (Б2П)"
    },
    {
      "bankName": "TKB",
      "identifier": "100000000034",
      "nameRus": "ТРАНСКАПИТАЛБАНК"
    },
    {
      "bankName": "SMP Bank",
      "identifier": "100000000036",
      "nameRus": "СМП Банк"
    },
    {
      "bankName": "GENBANK",
      "identifier": "100000000037",
      "nameRus": "ГЕНБАНК"
    },
    {
      "bankName": "FINAM",
      "identifier": "100000000040",
      "nameRus": "Банк ФИНАМ"
    },
    {
      "bankName": "BCS BANK",
      "identifier": "100000000041",
      "nameRus": "БКС Банк"
    },
    {
      "bankName": "UNISTREAM BANK",
      "identifier": "100000000042",
      "nameRus": "ЮНИСТРИМ БАНК"
    },
    {
      "bankName": "GAZENERGOBANK",
      "identifier": "100000000043",
      "nameRus": "Газэнергобанк"
    },
    {
      "bankName": "EXPOBANK",
      "identifier": "100000000044",
      "nameRus": "Экспобанк"
    },
    {
      "bankName": "BANK ZENIT",
      "identifier": "100000000045",
      "nameRus": "Банк ЗЕНИТ"
    },
    {
      "bankName": "METALLINVEST",
      "identifier": "100000000046",
      "nameRus": "Металлинвестбанк"
    },
    {
      "bankName": "ABSOLUT",
      "identifier": "100000000047",
      "nameRus": "Абсолют Банк"
    },
    {
      "bankName": "RRDB",
      "identifier": "100000000049",
      "nameRus": "Банк ВБРР"
    },
    {
      "bankName": "KUBAN CREDIT",
      "identifier": "100000000050",
      "nameRus": "Кубань Кредит"
    },
    {
      "bankName": "Bank Levoberezhniy",
      "identifier": "100000000052",
      "nameRus": "Банк Левобережный"
    },
    {
      "bankName": "Blanc bank",
      "identifier": "100000000053",
      "nameRus": "Бланк банк"
    },
    {
      "bankName": "Bank Yoshkar-Ola",
      "identifier": "100000000055",
      "nameRus": "Банк Йошкар-Ола"
    },
    {
      "bankName": "KHLYNOV",
      "identifier": "100000000056",
      "nameRus": "КБ Хлынов"
    },
    {
      "bankName": "VK Pay - Money.Mail.Ru",
      "identifier": "100000000057",
      "nameRus": "VK Pay - РНКО Деньги.Мэйл.Ру"
    },
    {
      "bankName": "Vladbusinessbank",
      "identifier": "100000000058",
      "nameRus": "ВЛАДБИЗНЕСБАНК"
    },
    {
      "bankName": "Centr-invest",
      "identifier": "100000000059",
      "nameRus": "Центр-инвест"
    },
    {
      "bankName": "MONETA",
      "identifier": "100000000061",
      "nameRus": "МОНЕТА"
    },
    {
      "bankName": "NOKSSBANK",
      "identifier": "100000000062",
      "nameRus": "НОКССБАНК"
    },
    {
      "bankName": "CREDIT URAL BANK",
      "identifier": "100000000064",
      "nameRus": "Кредит Урал Банк"
    },
    {
      "bankName": "Tochka (Bank Otkritie Financial Corporation)",
      "identifier": "100000000065",
      "nameRus": "ТОЧКА (ФК ОТКРЫТИЕ)"
    },
    {
      "bankName": "Zemsky bank",
      "identifier": "100000000066",
      "nameRus": "Земский банк"
    },
    {
      "bankName": "NC Bank",
      "identifier": "100000000067",
      "nameRus": "Новый век"
    },
    {
      "bankName": "SDM-Bank",
      "identifier": "100000000069",
      "nameRus": "СДМ-Банк"
    },
    {
      "bankName": "DATABANK",
      "identifier": "100000000070",
      "nameRus": "Датабанк"
    },
    {
      "bankName": "NS Bank",
      "identifier": "100000000071",
      "nameRus": "НС Банк"
    },
    {
      "bankName": "Bratsky Narodny Bank",
      "identifier": "100000000072",
      "nameRus": "Братский АНКБ"
    },
    {
      "bankName": "BANK SOYUZ",
      "identifier": "100000000078",
      "nameRus": "Банк СОЮЗ"
    },
    {
      "bankName": "ALMAZERGIENBANK",
      "identifier": "100000000080",
      "nameRus": "Алмазэргиэнбанк"
    },
    {
      "bankName": "Forshtadt",
      "identifier": "100000000081",
      "nameRus": "Форштадт"
    },
    {
      "bankName": "Bank DOM.RF",
      "identifier": "100000000082",
      "nameRus": "Банк ДОМ.РФ"
    },
    {
      "bankName": "FAR EASTERN BANK",
      "identifier": "100000000083",
      "nameRus": "Дальневосточный банк"
    },
    {
      "bankName": "RosDorBank",
      "identifier": "100000000084",
      "nameRus": "РосДорБанк"
    },
    {
      "bankName": "ELPLAT",
      "identifier": "100000000086",
      "nameRus": "ЭЛПЛАТ"
    },
    {
      "bankName": "PSCB",
      "identifier": "100000000087",
      "nameRus": "Банк ПСКБ"
    },
    {
      "bankName": "SCBP Primsotsbank",
      "identifier": "100000000088",
      "nameRus": "СКБ Примсоцбанк"
    },
    {
      "bankName": "BANK EKATERINBURG",
      "identifier": "100000000090",
      "nameRus": "Банк Екатеринбург"
    },
    {
      "bankName": "JSC BANK SNGB",
      "identifier": "100000000091",
      "nameRus": "БАНК СНГБ"
    },
    {
      "bankName": "BYSTROBANK",
      "identifier": "100000000092",
      "nameRus": "БыстроБанк"
    },
    {
      "bankName": "COALMETBANK",
      "identifier": "100000000093",
      "nameRus": "Углеметбанк"
    },
    {
      "bankName": "Chelyabinvestbank",
      "identifier": "100000000094",
      "nameRus": "ЧЕЛЯБИНВЕСТБАНК"
    },
    {
      "bankName": "ROSSIYA",
      "identifier": "100000000095",
      "nameRus": "АБ РОССИЯ"
    },
    {
      "bankName": "Uralfinance",
      "identifier": "100000000096",
      "nameRus": "Банк Уралфинанс"
    },
    {
      "bankName": "COMMERCIAL BANK ROSTFINANCE",
      "identifier": "100000000098",
      "nameRus": "КБ  РостФинанс"
    },
    {
      "bankName": "MODULBANK",
      "identifier": "100000000099",
      "nameRus": "КБ Модульбанк"
    },
    {
      "bankName": "ELECSNET",
      "identifier": "100000000100",
      "nameRus": "ЭЛЕКСНЕТ"
    },
    {
      "bankName": "Bank Agroros",
      "identifier": "100000000102",
      "nameRus": "Банк Агророс"
    },
    {
      "bankName": "CB Poidem",
      "identifier": "100000000103",
      "nameRus": "КБ Пойдём"
    },
    {
      "bankName": "SBI BANK",
      "identifier": "100000000105",
      "nameRus": "Эс-Би-Ай Банк"
    },
    {
      "bankName": "CHELINDBANK",
      "identifier": "100000000106",
      "nameRus": "ЧЕЛИНДБАНК"
    },
    {
      "bankName": "AKIBANK",
      "identifier": "100000000107",
      "nameRus": "АКИБАНК"
    },
    {
      "bankName": "ATB",
      "identifier": "100000000108",
      "nameRus": "Азиатско-Тихоокеанский Банк"
    },
    {
      "bankName": "CB Moskommertsbank",
      "identifier": "100000000110",
      "nameRus": "КБ Москоммерцбанк"
    },
    {
      "bankName": "SBER",
      "identifier": "100000000111",
      "nameRus": "Сбербанк"
    },
    {
      "bankName": "GARANT-INVEST BANK",
      "identifier": "100000000112",
      "nameRus": "ГАРАНТ-ИНВЕСТ БАНК"
    },
    {
      "bankName": "Alef-Bank",
      "identifier": "100000000113",
      "nameRus": "Алеф-Банк"
    },
    {
      "bankName": "NICO-BANK",
      "identifier": "100000000115",
      "nameRus": "НИКО-БАНК"
    },
    {
      "bankName": "ProBank",
      "identifier": "100000000117",
      "nameRus": "ПроБанк"
    },
    {
      "bankName": "CB Agropromcredit",
      "identifier": "100000000118",
      "nameRus": "КБ АГРОПРОМКРЕДИТ"
    },
    {
      "bankName": "CB SOLIDARNOST",
      "identifier": "100000000121",
      "nameRus": "КБ Солидарность"
    },
    {
      "bankName": "BANK ORENBURG",
      "identifier": "100000000124",
      "nameRus": "БАНК ОРЕНБУРГ"
    },
    {
      "bankName": "GORBANK",
      "identifier": "100000000125",
      "nameRus": "ГОРБАНК"
    },
    {
      "bankName": "KHAKAS MUNICIPAL",
      "identifier": "100000000127",
      "nameRus": "Хакасский муниципальный банк"
    },
    {
      "bankName": "CITIBANK",
      "identifier": "100000000128",
      "nameRus": "Ситибанк"
    },
    {
      "bankName": "BBR Bank",
      "identifier": "100000000133",
      "nameRus": "ББР Банк"
    },
    {
      "bankName": "NBD-Bank",
      "identifier": "100000000134",
      "nameRus": "НБД-Банк"
    },
    {
      "bankName": "ACCEPT",
      "identifier": "100000000135",
      "nameRus": "Банк Акцепт"
    },
    {
      "bankName": "METKOMBANK",
      "identifier": "100000000136",
      "nameRus": "МЕТКОМБАНК"
    },
    {
      "bankName": "First DorTransBank",
      "identifier": "100000000137",
      "nameRus": "Первый Дортрансбанк"
    },
    {
      "bankName": "Toyota Bank",
      "identifier": "100000000138",
      "nameRus": "Тойота Банк"
    },
    {
      "bankName": "CB ENERGOTRANSBANK",
      "identifier": "100000000139",
      "nameRus": "КБ ЭНЕРГОТРАНСБАНК"
    },
    {
      "bankName": "MB Bank",
      "identifier": "100000000140",
      "nameRus": "МБ Банк"
    },
    {
      "bankName": "URALPROMBANK",
      "identifier": "100000000142",
      "nameRus": "УРАЛПРОМБАНК"
    },
    {
      "bankName": "Bank 131",
      "identifier": "100000000143",
      "nameRus": "Банк 131"
    },
    {
      "bankName": "Timer Bank",
      "identifier": "100000000144",
      "nameRus": "Тимер Банк"
    },
    {
      "bankName": "KOSHELEV-BANK",
      "identifier": "100000000146",
      "nameRus": "КОШЕЛЕВ-БАНК"
    },
    {
      "bankName": "SINKO-BANK",
      "identifier": "100000000148",
      "nameRus": "СИНКО-БАНК"
    },
    {
      "bankName": "GUTA-BANK",
      "identifier": "100000000149",
      "nameRus": "ГУТА-БАНК"
    },
    {
      "bankName": "YANDEX BANK",
      "identifier": "100000000150",
      "nameRus": "Яндекс Банк"
    },
    {
      "bankName": "UralFD",
      "identifier": "100000000151",
      "nameRus": "Урал ФД"
    },
    {
      "bankName": "Togliattikhimbank",
      "identifier": "100000000152",
      "nameRus": "Тольяттихимбанк"
    },
    {
      "bankName": "Bank VENETS",
      "identifier": "100000000153",
      "nameRus": "Банк Венец"
    },
    {
      "bankName": "Bank Avers",
      "identifier": "100000000154",
      "nameRus": "Банк Аверс"
    },
    {
      "bankName": "BANK ITURUP",
      "identifier": "100000000158",
      "nameRus": "Банк ИТУРУП"
    },
    {
      "bankName": "Energobank",
      "identifier": "100000000159",
      "nameRus": "Энергобанк"
    },
    {
      "bankName": "Yug-Investbank",
      "identifier": "100000000160",
      "nameRus": "ЮГ-Инвестбанк"
    },
    {
      "bankName": "LOCKO-Bank",
      "identifier": "100000000161",
      "nameRus": "КБ ЛОКО-Банк"
    },
    {
      "bankName": "Bank Snezhinskiy",
      "identifier": "100000000163",
      "nameRus": "Банк Снежинский"
    },
    {
      "bankName": "KEB HNB RUS",
      "identifier": "100000000164",
      "nameRus": "КЭБ БАНК РУС"
    },
    {
      "bankName": "Russian Universal Bank",
      "identifier": "100000000165",
      "nameRus": "Русьуниверсалбанк"
    },
    {
      "bankName": "SIBSOCBANK",
      "identifier": "100000000166",
      "nameRus": "СИБСОЦБАНК"
    },
    {
      "bankName": "Evrofinance Mosnarbank",
      "identifier": "100000000167",
      "nameRus": "АКБ ЕВРОФИНАНС МОСНАРБАНК"
    },
    {
      "bankName": "World of Privilege Bank (MP Bank)",
      "identifier": "100000000169",
      "nameRus": "Мир Привилегий (МП Банк)"
    },
    {
      "bankName": "Banca Intesa",
      "identifier": "100000000170",
      "nameRus": "Банк Интеза"
    },
    {
      "bankName": "MARITIME BANK",
      "identifier": "100000000171",
      "nameRus": "МОРСКОЙ БАНК"
    },
    {
      "bankName": "DEVELOPMENT CAPITAL",
      "identifier": "100000000172",
      "nameRus": "Банк Развитие-Столица"
    },
    {
      "bankName": "Tavrichesky Bank",
      "identifier": "100000000173",
      "nameRus": "Таврический Банк"
    },
    {
      "bankName": "Finbank",
      "identifier": "100000000174",
      "nameRus": "Первый Инвестиционный Банк"
    },
    {
      "bankName": "JSCB TENDER BANK",
      "identifier": "100000000175",
      "nameRus": "АКБ Тендер Банк"
    },
    {
      "bankName": "MOSCOMBANK",
      "identifier": "100000000176",
      "nameRus": "МОСКОМБАНК"
    },
    {
      "bankName": "NOVIKOMBANK",
      "identifier": "100000000177",
      "nameRus": "НОВИКОМБАНК"
    },
    {
      "bankName": "Kuban Trade Bank",
      "identifier": "100000000180",
      "nameRus": "Кубаньторгбанк"
    },
    {
      "bankName": "Avtotorgbank",
      "identifier": "100000000181",
      "nameRus": "Автоторгбанк"
    },
    {
      "bankName": "Bаnk United capital",
      "identifier": "100000000182",
      "nameRus": "Банк Объединенный капитал"
    },
    {
      "bankName": "LLC CB GT bank",
      "identifier": "100000000183",
      "nameRus": "Газтрансбанк"
    },
    {
      "bankName": "JSCB NRBank",
      "identifier": "100000000184",
      "nameRus": "АКБ НРБанк"
    },
    {
      "bankName": "Natsinvestprombank",
      "identifier": "100000000185",
      "nameRus": "Нацинвестпромбанк"
    },
    {
      "bankName": "RESO CREDIT",
      "identifier": "100000000187",
      "nameRus": "Банк РЕСО Кредит"
    },
    {
      "bankName": "TATSOTSBANK",
      "identifier": "100000000189",
      "nameRus": "ТАТСОЦБАНК"
    },
    {
      "bankName": "BANK OF KAZAN",
      "identifier": "100000000191",
      "nameRus": "КБЭР Банк Казани"
    },
    {
      "bankName": "Bank IBA MOSCOW",
      "identifier": "100000000192",
      "nameRus": "Банк МБА МОСКВА"
    },
    {
      "bankName": "CB STROYLESBANK",
      "identifier": "100000000193",
      "nameRus": "КБ Стройлесбанк"
    },
    {
      "bankName": "RUSNARBANK",
      "identifier": "100000000194",
      "nameRus": "РУСНАРБАНК"
    },
    {
      "bankName": "Kuznetskbusinessbank",
      "identifier": "100000000195",
      "nameRus": "Кузнецкбизнесбанк"
    },
    {
      "bankName": "Inbank",
      "identifier": "100000000196",
      "nameRus": "Инбанк"
    },
    {
      "bankName": "Transstroibank",
      "identifier": "100000000197",
      "nameRus": "Трансстройбанк"
    },
    {
      "bankName": "Econombank",
      "identifier": "100000000198",
      "nameRus": "Экономбанк"
    },
    {
      "bankName": "ISBANK",
      "identifier": "100000000199",
      "nameRus": "ИШБАНК"
    },
    {
      "bankName": "JSCB SLAVIA",
      "identifier": "100000000200",
      "nameRus": "АКБ СЛАВИЯ"
    },
    {
      "bankName": "BANK KREMLYOVSKIY",
      "identifier": "100000000201",
      "nameRus": "Банк Кремлевский"
    },
    {
      "bankName": "Norvik Bank",
      "identifier": "100000000202",
      "nameRus": "Норвик Банк"
    },
    {
      "bankName": "INTERNATIONAL FINANCIAL CLUB",
      "identifier": "100000000203",
      "nameRus": "МЕЖДУНАРОДНЫЙ ФИНАНСОВЫЙ КЛУБ"
    },
    {
      "bankName": "American Express Bank",
      "identifier": "100000000204",
      "nameRus": "Америкэн Экспресс Банк"
    },
    {
      "bankName": "Bank Zarechye",
      "identifier": "100000000205",
      "nameRus": "Банк Заречье"
    },
    {
      "bankName": "Tomskpromstroybank",
      "identifier": "100000000206",
      "nameRus": "Томскпромстройбанк"
    },
    {
      "bankName": "Deutsche Bank",
      "identifier": "100000000207",
      "nameRus": "Дойче банк"
    },
    {
      "bankName": "SNB",
      "identifier": "100000000208",
      "nameRus": "Северный Народный Банк"
    },
    {
      "bankName": "Bank ALEKSANDROVSKY",
      "identifier": "100000000211",
      "nameRus": "Банк АЛЕКСАНДРОВСКИЙ"
    },
    {
      "bankName": "Crocus Bank",
      "identifier": "100000000212",
      "nameRus": "КБ Крокус Банк"
    },
    {
      "bankName": "J&T Bank, a.o.",
      "identifier": "100000000213",
      "nameRus": "Джей энд Ти Банк (АО)"
    },
    {
      "bankName": "VUZ-bank",
      "identifier": "100000000215",
      "nameRus": "ВУЗ-банк"
    },
    {
      "bankName": "Bank Finservice",
      "identifier": "100000000216",
      "nameRus": "Банк Финсервис"
    },
    {
      "bankName": "FORA-BANK",
      "identifier": "100000000217",
      "nameRus": "ФОРА-БАНК"
    },
    {
      "bankName": "SGB BANK",
      "identifier": "100000000219",
      "nameRus": "СЕВЕРГАЗБАНК"
    },
    {
      "bankName": "Novobank",
      "identifier": "100000000222",
      "nameRus": "Новобанк"
    },
    {
      "bankName": "SOCIUM BANK",
      "identifier": "100000000223",
      "nameRus": "СОЦИУМ БАНК"
    },
    {
      "bankName": "Belgorodsocbank",
      "identifier": "100000000225",
      "nameRus": "УКБ Белгородсоцбанк"
    },
    {
      "bankName": "PJSCB Primorye",
      "identifier": "100000000226",
      "nameRus": "Банк Приморье"
    },
    {
      "bankName": "CFB LLC",
      "identifier": "100000000227",
      "nameRus": "Банк БКФ"
    },
    {
      "bankName": "Prio-Vneshtorgbank",
      "identifier": "100000000228",
      "nameRus": "Прио-Внешторгбанк"
    },
    {
      "bankName": "MC Bank Rus",
      "identifier": "100000000229",
      "nameRus": "МС Банк Рус"
    },
    {
      "bankName": "Solid Bank",
      "identifier": "100000000230",
      "nameRus": "Солид Банк"
    },
    {
      "bankName": "CentroCredit Bank",
      "identifier": "100000000231",
      "nameRus": "Банк ЦентроКредит"
    },
    {
      "bankName": "Realist Bank",
      "identifier": "100000000232",
      "nameRus": "Реалист Банк"
    },
    {
      "bankName": "NK Bank",
      "identifier": "100000000233",
      "nameRus": "НК Банк"
    },
    {
      "bankName": "MOSCOW CITY BANK",
      "identifier": "100000000234",
      "nameRus": "БАНК МОСКВА СИТИ"
    },
    {
      "bankName": "PJSCB DERZHAVA",
      "identifier": "100000000235",
      "nameRus": "АКБ Держава"
    },
    {
      "bankName": "BANK IPB",
      "identifier": "100000000236",
      "nameRus": "Банк ИПБ"
    },
    {
      "bankName": "Industrial Savings Bank",
      "identifier": "100000000239",
      "nameRus": "ИС Банк"
    },
    {
      "bankName": "National Settlement Depository",
      "identifier": "100000000241",
      "nameRus": "Национальный расчетный депозитарий"
    },
    {
      "bankName": "JSC CB Lanta Bank",
      "identifier": "100000000245",
      "nameRus": "АКБ Ланта Банк"
    },
    {
      "bankName": "SME Bank",
      "identifier": "100000000246",
      "nameRus": "МСП Банк"
    },
    {
      "bankName": "DRIVE CLICK BANK",
      "identifier": "100000000250",
      "nameRus": "Драйв Клик Банк"
    },
    {
      "bankName": "Bank PTB",
      "identifier": "100000000255",
      "nameRus": "Банк ПТБ"
    },
    {
      "bankName": "Bank Vologzhanin",
      "identifier": "100000000257",
      "nameRus": "Банк Вологжанин"
    },
    {
      "bankName": "ENISEISK UNITED BANK",
      "identifier": "100000000258",
      "nameRus": "АИКБ Енисейский объединенный банк"
    },
    {
      "bankName": "Wildberries Bank",
      "identifier": "100000000259",
      "nameRus": "Wildberries (Вайлдберриз Банк)"
    },
    {
      "bankName": "HFB",
      "identifier": "100000000260",
      "nameRus": "Банк БЖФ"
    },
    {
      "bankName": "Perspektiva",
      "identifier": "100000000261",
      "nameRus": "НКО Перспектива"
    },
    {
      "bankName": "Royal Credit Bank",
      "identifier": "100000000263",
      "nameRus": "Роял Кредит Банк"
    },
    {
      "bankName": "CIFRA_BANK",
      "identifier": "100000000265",
      "nameRus": "Цифра банк"
    },
    {
      "bankName": "BANK ELITA",
      "identifier": "100000000266",
      "nameRus": "банк Элита"
    },
    {
      "bankName": "Stavropolpromstroybank",
      "identifier": "100000000267",
      "nameRus": "Ставропольпромстройбанк"
    },
    {
      "bankName": "Bank CHBDR",
      "identifier": "100000000269",
      "nameRus": "Банк ЧБРР"
    },
    {
      "bankName": "Dolinsk",
      "identifier": "100000000270",
      "nameRus": "КБ Долинск"
    },
    {
      "bankName": "Mobile card",
      "identifier": "100000000271",
      "nameRus": "Кошелек ЦУПИС (Мобильная карта)"
    },
    {
      "bankName": "Hice",
      "identifier": "100000000272",
      "nameRus": "Хайс"
    },
    {
      "bankName": "OZON",
      "identifier": "100000000273",
      "nameRus": "Озон Банк"
    },
    {
      "bankName": "Bank Perm",
      "identifier": "100000000274",
      "nameRus": "Банк Пермь"
    },
    {
      "bankName": "ELEKSIR NCO",
      "identifier": "100000000275",
      "nameRus": "НКО ЭЛЕКСИР"
    },
    {
      "bankName": "Altaykapitalbank",
      "identifier": "100000000276",
      "nameRus": "Алтайкапиталбанк"
    },
    {
      "bankName": "FINSTAR BANK",
      "identifier": "100000000278",
      "nameRus": "ФИНСТАР БАНК"
    },
    {
      "bankName": "Svoi Bank",
      "identifier": "100000000279",
      "nameRus": "Свой Банк"
    },
    {
      "bankName": "CMRBank",
      "identifier": "100000000282",
      "nameRus": "ЦМРБанк"
    },
    {
      "bankName": "PTB",
      "identifier": "100000000283",
      "nameRus": "НДБанк"
    },
    {
      "bankName": "TOCHKA BANK",
      "identifier": "100000000284",
      "nameRus": "Банк Точка"
    },
    {
      "bankName": "Promselhozbank Ltd",
      "identifier": "100000000285",
      "nameRus": "ООО Промсельхозбанк"
    },
    {
      "bankName": "Bank Orange LLC",
      "identifier": "100000000286",
      "nameRus": "Банк Оранжевый"
    },
    {
      "bankName": "YARINTERBANK",
      "identifier": "100000000293",
      "nameRus": "ЯРИНТЕРБАНК"
    },
    {
      "bankName": "Plait (Central Branch Sovcombank)",
      "identifier": "100000000296",
      "nameRus": "Плайт (филиал Центральный Совкомбанк)"
    }
]