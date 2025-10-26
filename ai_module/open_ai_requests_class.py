import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import httpx

class OpenAiRequestClass():
    def __init__(self, model_name: str):
        # Подгружаем переменные окружения
        load_dotenv()
        # создаём клиента для общения с гпт через прокси-сервер
        self.client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_TOKEN_STR"),
            http_client=httpx.AsyncClient(
                proxy=os.getenv("PROXY"),
                transport=httpx.HTTPTransport(local_address="0.0.0.0")
            )
        )
        self.model_name = model_name
    
    async def create_gpt_5_response(
        self,
        new_prompt: str,
        instruction_str: str
    ) -> str:

        preprompt = ( 
            f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на вопрос пользователя {new_prompt}, исходя из инструкции: {instruction_str}"
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": preprompt}
            ]
        )
        return response.choices[0].message.content

    # промпт до согласия на условия - второе сообщение пользователя
    async def get_gpt_5_response_before_agreement_point(
        self,
        new_prompt: str,
        instruction_str: str
    ) -> str:

        prompt_berofe_agreement = ( 
            f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на сообщение пользователя '{new_prompt}', исходя из инструкции: {instruction_str}. Попроси пользователя согласиться на наши правила из инструкции."
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt_berofe_agreement}
            ]
        )
        return response.choices[0].message.content
    
    # промпт после согласия и до подписки на канал
    async def get_gpt_5_response_after_agreement_and_before_subscription_point(
        self,
        new_prompt: str,
        instruction_str: str,
        CHANNEL_NAME: str
    ) -> str:

        prompt_subscription = ( 
            f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на сообщение пользователя '{new_prompt}', исходя из инструкции: {instruction_str}, попроси его подписаться на наш канал: {CHANNEL_NAME}"
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt_subscription}
            ]
        )
        return response.choices[0].message.content

    # промпт после согласия, подписки на канал , но до проверки наличия заказа товара
    async def get_gpt_5_response_after_subscription_and_before_order_point(
        self,
        new_prompt: str,
        instruction_str: str,
        CHANNEL_NAME: str
    ) -> str:

        prompt_order = ( 
            f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на сообщение пользователя '{new_prompt}', исходя из инструкции: {instruction_str}, нужно чтобы проверить пользователя на то, заказал ли он наш товар из инструкции."
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt_order}
            ]
        )
        return response.choices[0].message.content

    # промпт после согласия, подписки на канал , но до проверки наличия заказа товара
    async def get_gpt_5_response_after_order_and_before_receive_product_point(
        self,
        new_prompt: str,
        instruction_str: str,
        CHANNEL_NAME: str
    ) -> str:

        prompt_order = ( 
            f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на сообщение пользователя '{new_prompt}', исходя из инструкции: {instruction_str}, нужно проверить пользователя на то, получил ли он наш товар из инструкции."
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt_order}
            ]
        )
        return response.choices[0].message.content
    
    # промпт после согласия, подписки на канал , проверки наличия заказа товара, но до проверки наличия отзыва 
    async def get_gpt_5_response_after_receive_product_and_before_feedback_check_point(
        self,
        new_prompt: str,
        instruction_str: str,
        CHANNEL_NAME: str
    ) -> str:

        prompt_feedback = ( 
            f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на сообщение пользователя '{new_prompt}', исходя из инструкции: {instruction_str}, нужно проверить , оставил ли пользователь отзыв , согласно правилам в инструкции."
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt_feedback}
            ]
        )
        return response.choices[0].message.content
    
    # промпт после согласия, подписки на канал , проверки наличия заказа товара, проверки наличия отзыва , но до ШК
    async def get_gpt_5_response_after_feedback_and_before_shk_check_point(
        self,
        new_prompt: str,
        instruction_str: str,
        CHANNEL_NAME: str
    ) -> str:

        prompt_feedback = ( 
            f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Ответь кратко, четко, без лишней информации, своих размышлений на сообщение пользователя '{new_prompt}', исходя из инструкции: {instruction_str}, нужно проверить разрезал ли он этикетки(ШК) товара."
        )

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "user", "content": prompt_feedback}
            ]
        )
        return response.choices[0].message.content

    # промпт после согласия, подписки на канал , проверки наличия заказа товара, проверки наличия отзыва , ШК , но до реквизитов
    async def get_gpt_5_response_requisites(
        self,
        new_prompt: str,
        instruction_str: str,
        CHANNEL_NAME: str
    ) -> str:

        prompt_feedback = ( 
            f"Можешь в этом сообщении: '{new_prompt}' распознать номера банковской карты, номер телефона и денежную сумму в рублях?"
        )

        response = await self.client.chat.completions.create(
            model="gpt-5", # берем лучшую модель, чтобы она точно справилась
            messages=[
                {"role": "user", "content": prompt_feedback}
            ]
        )
        return response.choices[0].message.content