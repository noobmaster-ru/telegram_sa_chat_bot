import json
import logging
import re
from contextlib import suppress

from httpx import AsyncClient, AsyncHTTPTransport
from openai import AsyncOpenAI
from openai.types.responses import Response

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
            http_client=AsyncClient(proxy=config.proxy, transport=AsyncHTTPTransport(local_address="0.0.0.0")),
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
    ) -> dict[str, bool | str | int | None]:
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

        result = _extract_response_text(response)

        if not result:
            return {"is_order": False, "price": None, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.debug("classified order screenshot %s", result)
            return result

        return {"is_order": False, "price": None, "cancel_reason": None}

    async def classify_feedback_screenshot(
        self, photo_url: str, article_title: str, brand_name: str
    ) -> dict[str, bool | str | None]:
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

    async def classify_cut_labels_photo(self, photo_url: str) -> dict[str, str | bool | None]:
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

        result = _extract_response_text(response)

        if not result:
            return {"is_cut_labels": False, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.debug("classified cut labels screenshot %s", result)
            return result

        return {"is_cut_labels": False, "cancel_reason": None}

    async def answer_user_question(
        self,
        user_message: str,
        current_step: str,
        instruction_text: str,
        article_title: str,
        available_articles: list[tuple[int, str]] | None = None,
        chat_history: list[dict[str, str]] | None = None,
    ) -> dict[str, str | bool | int | None]:
        """
        Отвечает на вопрос пользователя в контексте кешбек-диалога.

        Returns:
            dict с ключами:
            - response: str - текст ответа
            - wants_to_stop: bool - хочет ли пользователь прекратить процесс
            - switch_to_article_id: int | None - ID артикула для переключения
        """
        step_descriptions = {
            "check_order": "отправка скриншота заказа на Wildberries",
            "check_received": "отправка скриншота отзыва с 5 звёздами",
            "check_labels_cut": "отправка фотографии разрезанных этикеток (штрихкодов/QR-кодов)",
        }
        current_step_desc = step_descriptions.get(current_step, "выполнение текущего шага")

        history_text = ""
        if chat_history:
            history_lines = []
            for entry in chat_history[-10:]:
                history_lines.append(f"Клиент: {entry['user']}")
                history_lines.append(f"Ты: {entry['assistant']}")
            history_text = "\n".join(history_lines)

        articles_text = ""
        articles_for_user = ""
        if available_articles:
            articles_lines = [f"- ID:{art_id} — {title}" for art_id, title in available_articles]
            articles_text = "\n".join(articles_lines)
            articles_for_user = "\n".join([f"- {title}" for _, title in available_articles])

        prompt = f"""
        Ты — вежливый помощник кешбек-сервиса. Клиент получает кешбек за покупку товара "{article_title}" на Wildberries.

        Процесс получения кешбека:
        1. Скриншот заказа — клиент отправляет скриншот оформленного заказа
        2. Скриншот отзыва — после получения товара клиент оставляет отзыв на 5 звёзд и присылает скриншот
        3. Фото разрезанных этикеток — клиент разрезает этикетки со штрихкодом/QR-кодом и присылает фото
        4. Реквизиты — клиент отправляет данные для перевода кешбека

        Сейчас клиент находится на шаге: {current_step_desc}

        Инструкция для клиента:
        {instruction_text}

        {"Доступные артикулы (ТОЛЬКО ДЛЯ СИСТЕМЫ, ID не показывать пользователю):" + chr(10) + articles_text if articles_text else ""}

        {"История диалога:" + chr(10) + history_text if history_text else ""}

        Новое сообщение клиента: "{user_message}"

        ВАЖНО:
        - Ответь кратко и по делу (не более 3-4 предложений)
        - Не повторяй ответы из истории диалога
        - НЕ добавляй завершающие фразы типа "Если возникнут вопросы — помогу"
        - Используй разметку Markdown
        - НИКОГДА не показывай пользователю ID артикулов — только названия товаров

        СПЕЦИАЛЬНЫЕ КОМАНДЫ (добавляй в начало ответа если нужно):

        1. Если клиент ОДНОЗНАЧНО хочет прекратить процесс по текущему товару
           (например: "не хочу", "отмена", "стоп", "передумал"),
           напиши [STOP] в начале ответа.

        2. Если клиент хочет получить кешбек за ДРУГОЙ товар из списка доступных,
           напиши [SWITCH:ID] где ID — числовой идентификатор из списка выше.
           Например: [SWITCH:123]
           После этого напиши приветствие для нового артикула (БЕЗ упоминания ID).

        3. Если клиент спрашивает какие товары доступны — перечисли ТОЛЬКО названия:
        {articles_for_user}

        Не путай вопросы или сомнения с командами — только явные намерения.
        """

        messages = [
            {"role": "system", "content": "Ты вежливый помощник кешбек-сервиса Wildberries."},
            {"role": "user", "content": prompt},
        ]

        response = await self._client.responses.create(
            model=CHAT_GPT_4O_LATEST,
            input=messages,
            temperature=0.7,
        )

        result = _extract_response_text(response)
        return _parse_answer_result(result)


def _extract_response_text(response: Response) -> str | None:
    """Извлекает текст ответа из response объекта OpenAI"""
    for item in response.output:
        if getattr(item, "content", None):
            for block in item.content:
                text = getattr(block, "text", None)
                if text:
                    return text.strip()
    return None


def _parse_answer_result(result: str | None) -> dict[str, str | bool | int | None]:
    """Парсит результат ответа GPT и извлекает специальные команды"""
    if not result:
        return {
            "response": "Пожалуйста, следуйте инструкциям на экране.",
            "wants_to_stop": False,
            "switch_to_article_id": None,
        }

    wants_to_stop = result.startswith("[STOP]")
    if wants_to_stop:
        result = result.replace("[STOP]", "").strip()

    switch_to_article_id = None
    if "[SWITCH:" in result:
        match = re.search(r"\[SWITCH:(\d+)\]", result)
        if match:
            switch_to_article_id = int(match.group(1))
            result = re.sub(r"\[SWITCH:\d+\]", "", result).strip()

    return {"response": result, "wants_to_stop": wants_to_stop, "switch_to_article_id": switch_to_article_id}
