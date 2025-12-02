import httpx
import logging
from openai import AsyncOpenAI
from src.tools.string_converter_class import StringConverter

class OpenAiRequestClass:
    def __init__(
        self, 
        OPENAI_API_KEY: str,
        GPT_MODEL_NAME: str,
        GPT_MODEL_NAME_PHOTO_ANALYSIS: str,
        PROXY: str,
        instruction_template: str,
        max_tokens: int,
        max_output_tokens_photo_analysis: int,
        temperature: float,
        reasoning: str
    ):
        # создаём клиента для общения с гпт через прокси-сервер
        self.client = AsyncOpenAI(
            api_key=OPENAI_API_KEY,
            http_client=httpx.AsyncClient(
                proxy=PROXY,
                transport=httpx.HTTPTransport(local_address="0.0.0.0")
            )
        )
        self.model_name = GPT_MODEL_NAME
        self.model_name_for_photo_analysis = GPT_MODEL_NAME_PHOTO_ANALYSIS
        self.instruction_template = instruction_template
        self.max_tokens = max_tokens 
        self.max_output_tokens_photo_analysis = max_output_tokens_photo_analysis
        self.temperature = temperature
        self.reasoning = reasoning
        # logging
        self.logger = logging.getLogger(__name__)

    async def _classify_photo(
        self,
        prefix_message: str,
        ref_image_url: str,
        user_image_url: str,
        nm_id: str,
        nm_id_name: str
    ) -> str:
        """
        Сравнивает две фотографии: эталон (reference) и присланную пользователем.
        Возвращает: 'Да' или 'Нет'
        """

        # формируем сообщение
        response = await self.client.responses.create(
            model=self.model_name_for_photo_analysis,  
            reasoning={
                "effort": self.reasoning
            },
            tools=[
                {
                    "type": "web_search",
                    "filters": {
                        "allowed_domains": [
                            "www.wildberries.ru"
                        ]
                    },
                    "user_location": {
                        "type": "approximate",
                        "country": "RU",
                        "city": "Moscow",
                        "region": "Moscow",
                    }
                }
            ],
            tool_choice="auto",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text", 
                            "text": (
                                "Ты — эксперт по визуальному сравнению изображений.\n"
                                "Первая фотография - это наш товар\n"
                                "Вторая фотография - скриншот ОТЗЫВА или ЗАКАЗА товара нашего клиента с Wildberries.\n"
                                f"{prefix_message}\n"
                                f"(Если не можешь классифицировать СКРИНШОТ: есть ли ОТЗЫВ или ЗАКАЗ именно НАШЕГО ТОВАРА, то можешь использовать веб-поиск(web_search), чтобы сверить внешний вид товара на сайте Wildberries. Находи на сайте Wilberries товар с таким id {nm_id}, название {nm_id_name})\n\n"
                                "Ответь строго одним словом: Да или Нет"
                            ),
                        },
                        {
                            "type": "input_image", 
                            "image_url": ref_image_url
                        },
                        {
                            "type": "input_image", 
                            "image_url": user_image_url
                        },
                    ]
                }
            ],
            max_output_tokens=self.max_output_tokens_photo_analysis
        )
        # self.logger.info(response)
        result = None
        for item in response.output:
            if getattr(item, "content", None):
                for block in item.content:
                    text = getattr(block, "text", None)
                    if text:
                        result = text.strip()
                        break
            if result:
                break

        if not result:
            self.logger.error("❌ Не удалось извлечь текст из ответа GPT")
            result = "Не удалось определить"
        usage = response.usage
        self.logger.info(
            f"  GPT usage — input: {usage.input_tokens}, "
            f"output: {usage.output_tokens}, "
            f"total: {usage.total_tokens}"
        )
        return result
    
    async def classify_photo_order(
        self, 
        ref_image_url: str,
        user_image_url: str,
        nm_id: str,
        nm_id_name: str
    ) -> str:
        """
        Отправляет фото модели GPT-5.1 и получает ответ: 'Да' или 'Нет'
        """
        return await self._classify_photo(
            prefix_message=f"Подумай и скажи есть ли на скриншоте ЗАКАЗ нашего товара на Wildberries. Название товара `{nm_id_name}` должно быть на скриншоте клиента. Также там могут быть надписи под названием: 'Оформляется', 'Вы оформили заказ', а на самом товаре надписи: 'Оплачен'(зелёным цветом) , 'НЕ ОПЛАЧЕН'(красным цветом)",
            ref_image_url=ref_image_url,
            user_image_url=user_image_url,
            nm_id=nm_id,
            nm_id_name=nm_id_name
        )
    
    async def classify_photo_feedback(
        self, 
        ref_image_url: str,
        user_image_url: str,
        nm_id: str,
        nm_id_name: str
    ) -> str:
        """
        Отправляет фото модели GPT-5.1 и получает ответ: 'Да' или 'Нет'
        """
        return await self._classify_photo(
            prefix_message=f"Подумай и скажи есть ли на скриншоте ОТЗЫВ на наш товар на Wildberries. Название товара `{nm_id_name}` и 5 оранжевых звёзд ⭐️ должны быть на скриншоте клиента. Звёзды могут быть прямо на фотографии товара.",
            ref_image_url=ref_image_url,
            user_image_url=user_image_url,
            nm_id=nm_id,
            nm_id_name=nm_id_name
        )
        
    async def classify_photo_shk(
        self, 
        user_image_url: str
    ) -> str:
        """
        Отправляет фото модели GPT-5.1 и получает ответ: 'Да' или 'Нет'
        """
        # формируем сообщение
        response = await self.client.responses.create(
            model=self.model_name_for_photo_analysis,  
            reasoning={
                "effort": self.reasoning
            },
            tool_choice="auto",
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text", 
                            "text": (
                                "Ты — эксперт по визуальному анализу изображений.\n"
                                f"Подумай ДОЛГО и скажи есть ли на фотографии клиента РАЗРЕЗАННЫЕ ЭТИКЕТКИ (Штрихкода) Wildberries нашего товара.\n"
                                "Ответь строго одним словом: Да или Нет"
                            ),
                        },
                        {
                            "type": "input_image", 
                            "image_url": user_image_url
                        },
                    ]
                }
            ],
            max_output_tokens=self.max_output_tokens_photo_analysis
        )
        # self.logger.info(response)
        result = None
        for item in response.output:
            if getattr(item, "content", None):
                for block in item.content:
                    text = getattr(block, "text", None)
                    if text:
                        result = text.strip()
                        break
            if result:
                break

        if not result:
            self.logger.error("❌ Не удалось извлечь текст из ответа GPT")
            result = "Не удалось определить"
        usage = response.usage
        self.logger.info(
            f"  GPT usage — input: {usage.input_tokens}, "
            f"output: {usage.output_tokens}, "
            f"total: {usage.total_tokens}"
        )
        return result
    
        # return await self._classify_photo(
        #     prefix_message="Подумай и скажи есть ли на фотографии клиента РАЗРЕЗАННЫЕ ЭТИКЕТКИ (Штрихкода) Wildberries нашего товара.",
        #     ref_image_url=ref_image_url,
        #     user_image_url=user_image_url,
        #     nm_id=nm_id,
        #     nm_id_name=nm_id_name
        # )
        
    async def _create_response(
        self,
        context_message: str,
        product_title: str
    ) -> str:
        """
        Базовый метод для общения с GPT — принимает текст подсказки (context_message),
        автоматически подставляет инструкцию и модель.
        """

        instruction_str = (
            self.instruction_template
            .replace("{", "{{").replace("}", "}}")
            .replace("{{product_title}}", "{product_title}")
        ).format(product_title=product_title)
        
        # 🧹 экранируем markdown-символы
        instruction_str = StringConverter.escape_markdown_v2(instruction_str) #re.sub(r"([_\[\]()~#+\-=|{}.!])", r"\\\1", instruction_str)

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
        # logging usage of tokens per prompt
        usage = response.usage
        self.logger.info(
            f"  GPT usage — input tokens: {usage.prompt_tokens}, output tokens: {usage.completion_tokens}"
        )
        return response.choices[0].message.content


    async def create_gpt_5_response(
        self, 
        new_prompt: str,
        product_title:str
    ) -> str:
        return await self._create_response(
            f"Покупатель уже выполнил наши правила: получил товар, оставил отзыв, "
            f"разрезал этикетки, отправил реквизиты. Ответь вежливо на вопрос: '{new_prompt}'",
            product_title=product_title
        )
   
    async def get_gpt_5_response_before_agreement_point(
        self, 
        new_prompt: str,
        product_title: str
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, покупатель должен согласиться с нашими правилами. "
            f"Ответь на его вопрос: '{new_prompt}' и попроси нажать на кнопку 'Да, согласен' в Telegram.",
            product_title=product_title
        )

    
    async def get_gpt_5_response_after_subscription_and_before_order_point(
        self, 
        new_prompt: str,
        product_title: str
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно проверить, заказал ли покупатель товар. "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, заказал'.",
            product_title=product_title
        )

    async def get_gpt_5_response_after_order_and_before_receive_product_point(
        self, 
        new_prompt: str,
        product_title: str
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно убедиться, что покупатель получил товар. "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, получил'.",
            product_title=product_title
        )

    async def get_gpt_5_response_after_receive_product_and_before_feedback_check_point(
        self, 
        new_prompt: str,
        product_title: str
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно проверить, оставил ли покупатель отзыв. "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, оставил'.",
            product_title=product_title
        )

    async def get_gpt_5_response_after_feedback_and_before_shk_check_point(
        self, 
        new_prompt: str,
        product_title: str
    ) -> str:
        return await self._create_response(
            f"Чтобы вернуть деньги, нужно убедиться, что покупатель разрезал этикетки (ШК). "
            f"Ответь на вопрос: '{new_prompt}' и попроси нажать 'Да, разрезал(а) ШК'.",
            product_title=product_title
        )
        
    async def create_gpt_5_response_requisites(
        self, 
        new_prompt: str,
        product_title: str
    ) -> str:
        return await self._create_response(
            f"Покупатель уже выполнил наши правила: получил товар, оставил отзыв, "
            f"разрезал этикетки, теперь ему нужно отправить нам реквизиты в формате:"
            f"Номер телефона: +7910XXXXXXX"
            f"Ответь вежливо на вопрос и попроси отправить реквизиты в описанном выше формате: '{new_prompt}'",
            product_title=product_title
        )