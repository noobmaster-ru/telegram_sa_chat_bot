import json
import logging
from contextlib import suppress

from httpx import AsyncClient, HTTPTransport
from openai import AsyncOpenAI

from axiomai.config import OpenAIConfig
from axiomai.constants import CHAT_GPT_4O_LATEST, CHAT_GPT_5_1, GPT_REASONING
from axiomai.infrastructure.database.models.cashback_table import CashbackArticle

logger = logging.getLogger(__name__)


PHOTO_ANALISE_TOOLS = [
    {
        "type": "web_search",
        "filters": {"allowed_domains": ["www.wildberries.ru"]},
        "user_location": {
            "type": "approximate",
            "country": "RU",
            "city": "Moscow",
            "region": "Moscow",
        },
    }
]


class OpenAIGateway:
    def __init__(self, config: OpenAIConfig) -> None:
        self._client = AsyncOpenAI(
            api_key=config.openai_api_key,
            http_client=AsyncClient(proxy=config.proxy, transport=HTTPTransport(local_address="0.0.0.0")),
        )

    async def classify_article_from_message(
        self, message_text: str, articles: list[CashbackArticle], photo_url: str | None = None
    ) -> CashbackArticle | None:
        if not articles:
            return None

        articles_list = "\n".join(f"{i + 1}. {article.title}" for i, article in enumerate(articles))

        prompt = f"""
        Определи, о каком товаре идёт речь на основе изображения и/или текста сообщения клиента.
        Список доступных товаров:
        {articles_list}

        Сообщение клиента: "{message_text}"

        Посмотри на текст или изображение. Если текст или изображение относятся к одному из товаров (даже частично), верни его ИНДЕКС из списка (1, 2, 3 и т.д.).
        Если не можешь определить товар, верни 0.

        Ответь ТОЛЬКО числом - индексом товара из списка (например: 1, 2, 3...) или 0, если товар не определён.
        """
        content: list[dict[str, str]] | str
        if photo_url:
            content = [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": photo_url},
            ]
        else:
            content = prompt

        messages = [
            {"role": "system", "content": "Ты помощник для классификации сообщений клиентов."},
            {"role": "user", "content": content},
        ]

        response = await self._client.responses.create(model=CHAT_GPT_4O_LATEST, input=messages, temperature=0)

        with suppress(ValueError, json.JSONDecodeError, AttributeError):
            result = int(response.output[0].content[0].text.strip())
            if 1 <= result <= len(articles):
                return articles[result - 1]

        return None

    async def classify_order_screenshot(
        self, photo_url: str, article_title: str, brand_name: str, article_image_url: str | None = None
    ) -> dict[str, bool | int | None]:
        prompt = f"""
        Проанализируй скриншот заказа на Wildberries и определи:
        1. Есть ли на скриншоте ЗАКАЗ нашего товара с названием "{article_title}" или бренд "{brand_name}"
        2. Какая цена указана для этого товара в рублях (₽)
        
        ВАЖНЫЕ признаки заказа на Wildberries:
        - Наличие слова "Заказы" в верхней части экрана
        - Рядом с карточкой товара есть статусы: "Оформляется", "Вы оформили заказ", "Оплачен" (зелёным), "НЕ ОПЛАЧЕН" (красным)
        - Карточка товара содержит изображение, название товара, бренд и цену
        
        Сравни изображение товара на скриншоте с эталонным изображением товара (если предоставлено).
        Товары должны визуально совпадать.
        
        Верни ответ в формате JSON: {{"is_order": bool, "price": int|null, "cancel_reason": str|null}}
        Где is_order = true, если заказ нашего товара присутствует на скриншоте,
        price = цена товара в рублях, или null если цена не видна,
        cancel_reason = причина отказа, если is_order = false
        """

        content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]

        if article_image_url:
            content.append({"type": "input_image", "image_url": article_image_url})

        messages = [
            {"role": "system", "content": "Ты помощник для анализа скриншотов заказов Wildberries."},
            {
                "role": "user",
                "content": content,
            },
        ]

        response = await self._client.responses.create(
            model=CHAT_GPT_5_1,
            input=messages,
            reasoning={"effort": GPT_REASONING},
            tools=PHOTO_ANALISE_TOOLS,
        )

        logger.debug("classified order screenshot response %s ", response)

        result = None
        for item in response.output:
            if getattr(item, "content", None):
                for block in item.content:
                    text = getattr(block, "text", None)
                    if text:
                        result = text.strip()
                        break

        if not result:
            return {"is_order": False, "price": None, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.debug("classified order screenshot %s", result)
            return result

        return {"is_order": False, "price": None, "cancel_reason": None}

    async def classify_feedback_screenshot(
        self, photo_url: str, article_title: str, brand_name: str
    ) -> dict[str, bool | None]:
        prompt = f"""
        Подумай и скажи есть ли на скриншоте ОТЗЫВ на наш товар на Wildberries.
        Подпись у товара может быть "{article_title}" или "{brand_name}" и 5 оранжевых звёзд ⭐️ должны быть на скриншоте клиента.
        Звёзды могут быть прямо на фотографии товара. Текст отзыва может и не быть, при этом звезды должны быть обязательно.
        
        Верни ответ в формате JSON: {{"is_feedback": bool, "cancel_reason": str|null}}
        Где is_feedback = true, если на скриншоте есть отзыв с 5 звёздами на наш товар,
        cancel_reason = причина отказа, если is_feedback = false
        """

        content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]

        messages = [
            {"role": "system", "content": "Ты помощник для анализа скриншотов отзывов Wildberries."},
            {
                "role": "user",
                "content": content,
            },
        ]

        response = await self._client.responses.create(
            model=CHAT_GPT_5_1,
            input=messages,
            reasoning={"effort": GPT_REASONING},
            tools=PHOTO_ANALISE_TOOLS,
        )

        logger.debug("classified feedback screenshot response %s ", response)

        result = None
        for item in response.output:
            if getattr(item, "content", None):
                for block in item.content:
                    text = getattr(block, "text", None)
                    if text:
                        result = text.strip()
                        break

        if not result:
            return {"is_feedback": False, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.debug("classified feedback screenshot %s", result)
            return result

        return {"is_feedback": False, "cancel_reason": None}

    async def classify_cut_labels_photo(self, photo_url: str) -> dict[str, bool | None]:
        prompt = """
        Подумай и скажи есть ли на фотографии клиента РАЗРЕЗАННЫЕ ЭТИКЕТКИ (Штрихкода или QR-кода) Wildberries нашего товара.
        
        Верни ответ в формате JSON: {"is_cut_labels": bool, "cancel_reason": str|null}
        Где is_cut_labels = true, если на фотографии есть разрезанные этикетки Wildberries,
        cancel_reason = причина отказа, если is_cut_labels = false
        """

        content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]

        messages = [
            {"role": "system", "content": "Ты помощник для анализа фотографий разрезанных этикеток Wildberries."},
            {
                "role": "user",
                "content": content,
            },
        ]

        response = await self._client.responses.create(
            model=CHAT_GPT_5_1,
            input=messages,
            reasoning={"effort": GPT_REASONING},
            tools=PHOTO_ANALISE_TOOLS,
        )

        logger.debug("classified cut labels screenshot response %s ", response)

        result = None
        for item in response.output:
            if getattr(item, "content", None):
                for block in item.content:
                    text = getattr(block, "text", None)
                    if text:
                        result = text.strip()
                        break

        if not result:
            return {"is_cut_labels": False, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.debug("classified cut labels screenshot %s", result)
            return result

        return {"is_cut_labels": False, "cancel_reason": None}
