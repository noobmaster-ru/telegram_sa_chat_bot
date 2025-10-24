# import os
# from dotenv import load_dotenv
# from openai import OpenAI


# def create_gpt_5_response(
#     telegram_id: int,
#     new_prompt: str,
#     instruction_str: str
# ) -> str:
#     # Подгружаем переменные окружения
#     load_dotenv()

#     OPENAI_TOKEN = os.getenv("OPENAI_TOKEN_STR")
#     client = OpenAI(api_key=OPENAI_TOKEN)

#     preprompt = ( 
#         f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на вопрос пользователя {new_prompt}, исходя из инструкции: {instruction_str},  если пользователь написал #выплата_DD_MONTH, то пиши в чат ВЫПЛАТА_ПРИНИМАЕТСЯ, иначе пиши в чат: 'Вы неправильно указали дату выплаты, исправьте по шаблону: #выплата_DD_MONTH'"
#     )

#     response = client.chat.completions.create(
#         model="gpt-5-mini",
#         messages=[
#             {"role": "user", "content": preprompt}
#         ]
#     )
#     return response.choices[0].message.content
