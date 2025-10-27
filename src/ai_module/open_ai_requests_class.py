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
        instruction_str: str
    ):
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
                    "role": "user", 
                    "content": f"Инструкция: '{self.instruction_str}'. Запомни это. Ты чат помощник маркетплейса, нам нужно научить покупателей оставлять отзыв. Твоя цель - чтобы покупатель научился оставлять отзыв и был доволен покупкой. Ответь на вопрос пользователя: {new_prompt}"
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
                    "role": "user", 
                    "content": f"Инструкция: '{self.instruction_str}'. Запомни это. Ты чат помощник маркетплейса, нам нужно научить покупателей оставлять отзыв. Твоя цель - чтобы покупатель научился оставлять отзыв и был доволен покупкой. Ответь на вопрос пользователя: '{new_prompt}' и попроси его также нажать на кнопку соглашения с нашими условиями в Telegram ниже "
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
                    "role": "user", 
                    "content": f"Инструкция: '{self.instruction_str}'. Запомни это. Ты чат помощник маркетплейса, нам нужно научить покупателей оставлять отзыв. Твоя цель - чтобы покупатель научился оставлять отзыв и был доволен покупкой. Ответь на вопрос пользователя: '{new_prompt}' и попроси его также подписать на наш канал {CHANNEL_NAME} и после нажать на кнопку 'Да, подписался'."
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
                    "role": "user", 
                    "content": f"Инструкция: '{self.instruction_str}'. Запомни это. Ты чат помощник маркетплейса, нам нужно научить покупателей оставлять отзыв. Твоя цель - чтобы покупатель научился оставлять отзыв и был доволен покупкой. Ответь на вопрос пользователя: '{new_prompt}' и проверь заказал ли он товар, если заказал, то попроси его нажать на кнопку 'Да, заказал'"
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
                    "role": "user", 
                    "content": f"Инструкция: '{self.instruction_str}'. Запомни это. Ты чат помощник маркетплейса, нам нужно научить покупателей оставлять отзыв. Твоя цель - чтобы покупатель научился оставлять отзыв и был доволен покупкой. Ответь на вопрос пользователя: '{new_prompt}' и проверь, что он получил товар, если получил, то попроси его нажать на кнопку 'Да, получил'"
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
                    "role": "user", 
                    "content": f"Инструкция: '{self.instruction_str}'. Запомни это. Ты чат помощник маркетплейса, нам нужно научить покупателей оставлять отзыв. Твоя цель - чтобы покупатель научился оставлять отзыв и был доволен покупкой. Ответь на вопрос пользователя: '{new_prompt}' и проверь оставил ли он отзыв как нужно , если оставил, то попроси его нажать на кнопку 'Да, оставил'"
                }
            ],
            model=self.model_name
        )
        return response.choices[0].message.content
    
    # промпт после согласия, подписки на канал , проверки наличия заказа товара, проверки наличия отзыва , но до ШК
    async def get_gpt_5_response_after_feedback_and_before_shk_check_point(self, new_prompt: str) -> str:
        response = await self.client.chat.completions.create(
            messages=[
                {
                    "role": "user", 
                    "content": f"Инструкция: '{self.instruction_str}'. Запомни это. Ты чат помощник маркетплейса, нам нужно научить покупателей оставлять отзыв. Твоя цель - чтобы покупатель научился оставлять отзыв и был доволен покупкой. Ответь на вопрос пользователя: '{new_prompt}' и проверь разрезал ли он этикетки , если разрезал, то попроси его нажать на кнопку 'Да, разрезал'"
                }
            ],
            model=self.model_name
        )
        return response.choices[0].message.content