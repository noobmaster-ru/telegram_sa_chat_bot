import os
from dotenv import load_dotenv
from openai import OpenAI
from db.database import add_message, get_chat_history


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

    # 1️⃣ Добавляем сообщение пользователя в БД
    add_message(telegram_id, "user", new_prompt)

    # 2️⃣ Получаем историю диалога
    messages_history = get_chat_history(telegram_id, limit=NUMBER_OF_HISTORY_MESSAGE)
    
    system_content = ( 
        f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, четко, без лишней информации , своих размышлений на вопросы пользователя , исходя из инструкции: {instruction_str},  если пользователь написал #выплата_DD_MONTH, то пиши в чат ВЫПЛАТА_ПРИНИМАЕТСЯ, иначе пиши в чат: 'Вы неправильно указали дату выплаты, исправьте по шаблону: #выплата_DD_MONTH'"
    )

    # 3️⃣ Добавляем системное сообщение, список прошлых сообщений и текущий вопрос
    messages = [{"role": "system", "content": system_content}] + messages_history
    try:
        completion = client.chat.completions.create(
            model="gpt-5-mini",  
            messages=messages,
            # max_completion_tokens=400
        )
        response_text = completion.choices[0].message.content
        
        # 5️⃣ Сохраняем ответ в БД
        add_message(telegram_id, "assistant", response_text)
        
        return response_text
    except Exception as e:
        return f"[ERROR] GPT запрос не удался: {e}"