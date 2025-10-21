import os
from dotenv import load_dotenv
from gigachat import GigaChat



def create_response(
    question: str,
    instruction_str: str
) -> str:
    # Подгружаем переменные окружения
    load_dotenv()

    GIGACHAT_TOKEN = os.getenv("GIGACHAT_TOKEN_STR")
    giga = GigaChat(
        credentials=GIGACHAT_TOKEN,
        verify_ssl_certs=False,
        #    scope="GIGACHAT_API_PERS",
        model="GigaChat-2-Max",
    )
    preprompt = ( 
        f"Ты мой помощник. Ты отвечаешь на сообщения людей в телеграме. Ответь кратко, четко, без лишней информации , своих размышлений на вопрос пользователя '{question}', исходя из инструкции: {instruction_str}; если пользователь написал #выплата_DD_MONTH, то пиши в чат ВЫПЛАТА_ПРИНИМАЕТСЯ, иначе пиши в чат: 'Вы неправильно указали дату выплаты, исправьте по шаблону: #выплата_DD_MONTH'"
    )
    response = giga.chat(preprompt)
    return response.choices[0].message.content