import os
from dotenv import load_dotenv
from openai import OpenAI
from db.database import add_message, get_chat_history


def get_gpt_5_response_with_context(client: OpenAI, list_of_history_messages_and_new_question: list):
    """Отправляет список сообщений в API и возвращает ответ."""
    try:
        completion = client.chat.completions.create(
            model="gpt-5",  # Используйте актуальную модель
            messages=list_of_history_messages_and_new_question,
            # max_completion_tokens=400
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"[ERROR] get_gpt_response_with_context: {e}"
    
def create_gpt_5_response(
    telegram_id: int,
    new_prompt: str,
    instruction_str: str
) -> str:
    # Подгружаем переменные окружения
    load_dotenv()

    OPENAI_TOKEN = os.getenv("OPENAI_TOKEN_STR")
    NUMBER_OF_HISTORY_MESSAGE = int(os.getenv("NUMBER_OF_HISTORY_MESSAGE_INT"))
    client = OpenAI(api_key=OPENAI_TOKEN)


    system_content = ( 
        f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, четко, без лишней информации , своих размышлений на вопрос пользователя , исходя из инструкции: {instruction_str},  если пользователь написал #выплата_DD_MONTH, то пиши в чат ВЫПЛАТА_ПРИНИМАЕТСЯ, иначе пиши в чат: 'Вы неправильно указали дату выплаты, исправьте по шаблону: #выплата_DD_MONTH'"
    )
    # 1️⃣ Загружаем историю из БД
    history = get_chat_history(telegram_id, limit=NUMBER_OF_HISTORY_MESSAGE)

    # 2️⃣ Добавляем системное сообщение, список прошлых сообщений и текущий вопрос
    messages_history = [{"role": "system", "content": system_content}] + history
    messages_history.append({"role": "user", "content": new_prompt})
    # messages_history = [
    #     {"role": "system", "content": "Вы полезный ассистент, помогающий с информацией о продукте."},
    #     # Исторические запросы пользователя
    #     {"role": "user", "content": "можете выслать инструкцию?"},
    #     {"role": "assistant", "content": "Конечно, вот инструкция по эксплуатации товара. [Тут должен быть текст ответа ассистента на первый вопрос]."},
    #     {"role": "user", "content": "какой артикул покупать?"},
    #     {"role": "assistant", "content": "Чтобы я мог подсказать артикул, уточните, пожалуйста, для какой модели товара вы его ищете."},
    #     {"role": "user", "content": "что мне сделать ,чтобы деньги получить?"}
    # ]

    # 3️⃣ Отправляем в API
    response_text = get_gpt_5_response_with_context(
        client=client, 
        list_of_history_messages_and_new_question=messages_history
    )

    # 4️⃣ Сохраняем в БД оба сообщения
    add_message(telegram_id, "user", new_prompt)
    add_message(telegram_id, "assistant", response_text)
    return response_text
    # response = client.chat.completions.create(
    #     model="gpt-5",
    #     messages=[
    #         {"role": "system", "content": preprompt},
    #         {"role": "user", "content": question}
    #     ]
    # )
    # return response.choices[0].message.content
