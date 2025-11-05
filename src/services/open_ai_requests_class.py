import os
import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI
import logging
import re
import json
from datetime import datetime
from zoneinfo import ZoneInfo

class OpenAiRequestClass:
    def __init__(
        self, 
        OPENAI_API_KEY: str,
        GPT_MODEL_NAME_STR: str,
        PROXY: str,
        instruction_template: str,
        max_tokens: int,
        temperature: float
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
        self.instruction_template = instruction_template
        self.max_tokens = max_tokens 
        self.temperature = temperature

    async def _create_response(
        self,
        context_message: str,
        nm_id: str,
        count: int
    ) -> str:
        """
        Базовый метод для общения с GPT — принимает текст подсказки (context_message),
        автоматически подставляет инструкцию и модель.
        """
        # готовим дату, чтобы вставить её в инструкцию today_date
        months = {
            1: "января", 2: "февраля", 3: "марта", 4: "апреля",
            5: "мая", 6: "июня", 7: "июля", 8: "августа",
            9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
        }
        today = datetime.now(ZoneInfo("Europe/Moscow"))
        today_date = f"{today.day}_{months[today.month]}"

        instruction_str = (
            self.instruction_template
            .replace("{", "{{").replace("}", "}}")
            .replace("{{nm_id}}", "{nm_id}")
            .replace("{{today_date}}", "{today_date}")
            .replace("{{count}}", "{count}")
        ).format(nm_id=nm_id, count=count ,today_date=today_date)
        
        # 🧹 экранируем markdown-символы
        instruction_str = re.sub(r"([_\[\]()~#+\-=|{}.!])", r"\\\1", instruction_str)

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Вот наши правила на возврат средств за товар: '{instruction_str}'."
                        f"{context_message}"
                    )
                }
            ],
            max_tokens=self.max_tokens,          # ограничиваем длину ответа 
            temperature=self.temperature,         # снижает «творчество» ради скорости и стабильности
            # timeout=12,              # чтобы не ждать вечно
        )
        return response.choices[0].message.content


    async def create_gpt_5_response(
        self, 
        new_prompt: str,
        nm_id: str,
        count: int
    ) -> str:
        return await self._create_response(
            f"Покупатель уже выполнил наши правила: получил товар, оставил отзыв, "
            f"разрезал этикетки, отправил реквизиты. Ответь вежливо на вопрос: '{new_prompt}'",
            nm_id=nm_id,
            count=count
        )
   
    
    async def get_gpt_5_response_before_agreement_point(
        self, 
        new_prompt: str,
        nm_id: str,
        count: int 
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, покупатель должен согласиться с нашими правилами. "
            f"Ответь на его вопрос: '{new_prompt}' и попроси нажать на кнопку 'Да, согласен' в Telegram.",
            nm_id=nm_id,
            count=count
        )


    async def get_gpt_5_response_after_agreement_and_before_subscription_point(
        self, 
        new_prompt: str, 
        CHANNEL_NAME: str,
        nm_id: str,
        count: int 
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, покупатель должен подписаться на канал {CHANNEL_NAME}. "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать на кнопку 'Да, подписался'.",
            nm_id=nm_id,
            count=count
        )
    
    
    async def get_gpt_5_response_after_subscription_and_before_order_point(
        self, 
        new_prompt: str,
        nm_id: str,
        count: int
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно проверить, заказал ли покупатель товар. "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, заказал'.",
            nm_id=nm_id,
            count=count
        )


    async def get_gpt_5_response_after_order_and_before_receive_product_point(
        self, 
        new_prompt: str,
        nm_id: str,
        count: int
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно убедиться, что покупатель получил товар. "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, получил'.",
            nm_id=nm_id,
            count=count
        )


    async def get_gpt_5_response_after_receive_product_and_before_feedback_check_point(
        self, 
        new_prompt: str,
        nm_id: str,
        count: int
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно проверить, оставил ли покупатель отзыв. "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, оставил'.",
            nm_id=nm_id,
            count=count
        )


    async def get_gpt_5_response_after_feedback_and_before_shk_check_point(
        self, 
        new_prompt: str,
        nm_id: str,
        count: int
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно убедиться, что покупатель разрезал этикетки (ШК). "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, разрезал(а) ШК'.",
            nm_id=nm_id,
            count=count
        )
        
    async def create_gpt_5_response_requisites(
        self, 
        new_prompt: str,
        nm_id: str,
        count: int
    ) -> str:
        return await self._create_response(
            f"Покупатель уже выполнил наши правила: получил товар, оставил отзыв, "
            f"разрезал этикетки, теперь ему нужно отправить нам реквизиты в формате:"
            f"- Номер карты: AAAA BBBB CCCC DDDD или\n- Номер телефона: 8910XXXXXXX \n- Название банка: Сбербанк, Т-банк\n-Cумму для оплаты: 500 рублей"
            f"Ответь вежливо на вопрос и попроси отправить реквизиты описанном выше формате: '{new_prompt}'",
            nm_id=nm_id,
            count=count
        )