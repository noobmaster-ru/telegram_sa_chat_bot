import os
from dotenv import load_dotenv
from gigachat import GigaChat



def create_response(text: str):
    # Подгружаем переменные окружения
    load_dotenv()

    GIGACHAT_TOKEN = os.getenv("GIGACHAT_TOKEN_STR")
    giga = GigaChat(
    credentials=GIGACHAT_TOKEN,
    verify_ssl_certs=False
    #    scope="GIGACHAT_API_PERS",
    #    model="GigaChat",
    )
    response = giga.chat(text)
    return response.choices[0].message.content