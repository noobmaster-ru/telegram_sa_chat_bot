from contextlib import suppress
import json

from openai import AsyncOpenAI

from axiomai.application.dto import CashbackArticle
from axiomai.config import Config


class OpenAIGateway:
    def __init__(self, config: Config) -> None:
        self._client = AsyncOpenAI(api_key=config.openai_api_key)

    async def classify_article_from_message(
        self, message_text: str, articles: list[CashbackArticle], photo_url: str | None = None
    ) -> CashbackArticle | None:
        if not articles:
            return None

        articles_list = "\n".join(f"{i+1}. {article.title}" for i, article in enumerate(articles))

        prompt = f"""
        Определи, о каком товаре идёт речь на основе изображения и/или текста сообщения клиента.
        Список доступных товаров:
        {articles_list}

        Сообщение клиента: "{message_text}"

        Посмотри на текст или изображение. Если текст или изображение относятся к одному из товаров (даже частично), верни его ИНДЕКС из списка (1, 2, 3 и т.д.).
        Если не можешь определить товар, верни 0.

        Ответь ТОЛЬКО числом - индексом товара из списка (например: 1, 2, 3...) или 0, если товар не определён.
        """

        if photo_url:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": photo_url}},
            ]
        else:
            content = prompt

        messages = [
            {"role": "system", "content": "Ты помощник для классификации сообщений клиентов."},
            {"role": "user", "content": content},
        ]

        response = await self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
        )

        with suppress(ValueError, IndexError, AttributeError):
            result = int(response.choices[0].message.content.strip())
            if 1 <= result <= len(articles):
                return articles[result - 1]

        return None

    async def classify_order_screenshot(
        self, photo_url: str, article_title: str, brand_name: str, article_image_url: str | None = None
    ) -> dict[str, bool | int | None]:
        prompt = f"""
        Проанализируй скриншот заказа на Wildberries и определи:
        1. Есть ли на скриншоте ЗАКАЗ нашего товара с названием '{article_title}' или бренд '{brand_name}'
        2. Какая цена указана для этого товара в рублях (₽)
        
        ВАЖНЫЕ признаки заказа на Wildberries:
        - Наличие слова "Заказы" в верхней части экрана
        - Рядом с карточкой товара есть статусы: "Оформляется", "Вы оформили заказ", "Оплачен" (зелёным), "НЕ ОПЛАЧЕН" (красным)
        - Карточка товара содержит изображение, название товара, бренд и цену
        
        Сравни изображение товара на скриншоте с эталонным изображением товара (если предоставлено).
        Товары должны визуально совпадать.
        
        Верни ответ в формате JSON: {{'is_order': bool, 'price': int|null}}
        Где is_order = true, если заказ нашего товара присутствует на скриншоте
        price = цена товара в рублях, или null если цена не видна
        """

        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": photo_url}},
        ]

        if article_image_url:
            content.append({"type": "image_url", "image_url": {"url": article_image_url}})

        messages = [
            {"role": "system", "content": "Ты помощник для анализа скриншотов заказов Wildberries."},
            {
                "role": "user",
                "content": content,
            },
        ]

        response = await self._client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            temperature=0,
        )

        with suppress(ValueError, json.JSONDecodeError, AttributeError):
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            return result

        return {"is_order": False, "price": None}

    async def classify_feedback_screenshot(
        self, photo_url: str, article_title: str, brand_name: str
    ) -> dict[str, bool]:
        prompt = f"""
        Подумай и скажи есть ли на скриншоте ОТЗЫВ на наш товар на Wildberries.
        Название товара `{article_title}`, бренда {brand_name} и 5 оранжевых звёзд ⭐️ должны быть на скриншоте клиента. Звёзды могут быть прямо на фотографии товара.
        
        Верни ответ в формате JSON: {{'is_feedback': bool}}
        Где is_review = true, если на скриншоте есть отзыв с 5 звёздами на наш товар
        """

        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": photo_url}},
        ]

        messages = [
            {"role": "system", "content": "Ты помощник для анализа скриншотов отзывов Wildberries."},
            {
                "role": "user",
                "content": content,
            },
        ]

        response = await self._client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            temperature=0,
        )

        with suppress(ValueError, json.JSONDecodeError, AttributeError):
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            return result

        return {"is_review": False}

    async def classify_cut_labels_photo(self, photo_url: str) -> dict[str, bool]:
        prompt = """
        Подумай ДОЛГО и скажи есть ли на фотографии клиента РАЗРЕЗАННЫЕ ЭТИКЕТКИ (Штрихкода или QR-кода) Wildberries нашего товара.
        
        Верни ответ в формате JSON: {'is_cut_labels': bool}
        Где is_cut_labels = true, если на фотографии есть разрезанные этикетки Wildberries
        """

        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": photo_url}},
        ]

        messages = [
            {"role": "system", "content": "Ты помощник для анализа фотографий разрезанных этикеток Wildberries."},
            {
                "role": "user",
                "content": content,
            },
        ]

        response = await self._client.chat.completions.create(
            model="gpt-5.1",
            messages=messages,
            temperature=0,
        )

        with suppress(ValueError, json.JSONDecodeError, AttributeError):
            content = response.choices[0].message.content.strip()
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            return result

        return {"is_cut_labels": False}
