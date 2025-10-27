import os
import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

class OpenAiRequestClass():
    def __init__(
        self, 
        OPENAI_API_KEY: str,
        GPT_MODEL_NAME_STR: str,
        PROXY: str,
        instruction_str: str):
        # Подгружаем переменные окружения
        load_dotenv()
        # создаём клиента для общения с гпт через прокси-сервер
        self.client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            http_client=httpx.AsyncClient(
                proxy=PROXY,
                transport=httpx.HTTPTransport(local_address="0.0.0.0")
            )
        )
        self.model_name = GPT_MODEL_NAME_STR
        self.instruction_str = instruction_str
    
    async def create_gpt_5_response(self,new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, без своих размышлений на сообщения пользователей , исходя из инструкции: {self.instruction_str}"
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ],
            model=self.model_name,
        )
        return response.choices[0].message.content

    # промпт до согласия на условия - второе сообщение пользователя
    async def get_gpt_5_response_before_agreement_point(self, new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, без своих размышлений на сообщения пользователей. Мы предоставляем сервис по кэшбеку товаров на Wildberries за отзывы.Попроси пользователя согласиться на наши правила из инструкции, нажав на кнопку Telegram ниже, сказав, что без согласия мы не сможем отправить пользователю кэшбек"
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ],
            model=self.model_name
        )
        return response.choices[0].message.content
    
    # промпт после согласия и до подписки на канал
    async def get_gpt_5_response_after_agreement_and_before_subscription_point(
        self,
        new_prompt: str,
        CHANNEL_NAME: str
    ) -> str:


        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, без своих размышлений на сообщения пользователей. Попроси его подписаться на наш канал: {CHANNEL_NAME}"
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ],
            model=self.model_name,
        )
        return response.choices[0].message.content

    # промпт после согласия, подписки на канал , но до проверки наличия заказа товара
    async def get_gpt_5_response_after_subscription_and_before_order_point(self, new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, без своих размышлений на сообщения пользователей. Нужно проверить пользователя на то, заказал ли он наш товар из инструкции, если он написал, что 'заказал/а', то попроси его нажать на кнопку Telegram ниже"
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ],
            model=self.model_name
        )
        return response.choices[0].message.content

    # промпт после согласия, подписки на канал , но до проверки наличия заказа товара
    async def get_gpt_5_response_after_order_and_before_receive_product_point(self, new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, без своих размышлений на сообщения пользователей. Нужно проверить пользователя на то, получил ли он наш товар из инструкции, если он написал, что 'получил/а', то попроси его нажать на кнопку Telegram ниже."
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ],
            model=self.model_name
        )
        return response.choices[0].message.content
    
    # промпт после согласия, подписки на канал , проверки наличия заказа товара, но до проверки наличия отзыва 
    async def get_gpt_5_response_after_receive_product_and_before_feedback_check_point(self, new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, без своих размышлений на сообщения пользователей. Нужно проверить пользователя на то, поставил ли он отзыв, если он написал, что 'оставил/а', то попроси его нажать на кнопку Telegram ниже"
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ],
            model=self.model_name,
        )
        return response.choices[0].message.content
    
    # промпт после согласия, подписки на канал , проверки наличия заказа товара, проверки наличия отзыва , но до ШК
    async def get_gpt_5_response_after_feedback_and_before_shk_check_point(self, new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "system", 
                    "content": f"Ты мой помощник. Ты отвечаешь на сообщения людей в Telegram. Отвечай кратко, без своих размышлений на сообщения пользователей. Нужно проверить пользователя на то, разрезал ли он этикетки(ШК) товара, если он написал, что 'разрезал/а', то попроси его нажать на кнопку Telegram ниже"
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ]
        )
        return response.choices[0].message.content

    # промпт после согласия, подписки на канал , проверки наличия заказа товара, проверки наличия отзыва , ШК , но до реквизитов
    async def get_gpt_5_response_requisites(self, new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": f"Можешь в сообщении пользователя распознать номера банковской карты, номер телефона и денежную сумму в рублях?"
                },
                {
                    "role": "user", 
                    "content": new_prompt
                }
            ],
            model="gpt-5", # берем лучшую модель, чтобы она точно справилась
        )
        return response.choices[0].message.content