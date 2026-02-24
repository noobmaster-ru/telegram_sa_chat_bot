import json
import logging
import re
from contextlib import suppress
from typing import TypedDict

from httpx import AsyncClient, AsyncHTTPTransport
from openai import AsyncOpenAI
from openai.types.responses import Response

from axiomai.config import OpenAIConfig
from axiomai.constants import (
    GPT_MAX_OUTPUT_TOKENS,
    GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
    GPT_REASONING,
    MODEL_NAME,
)
from axiomai.infrastructure.database.models import Buyer
from axiomai.infrastructure.database.models.cashback_table import CashbackArticle

logger = logging.getLogger(__name__)

class ChatHistoryEntry(TypedDict):
    user: str
    assistant: str

class ClassifyOrderResult(TypedDict):
    is_order: bool
    nm_id: int | None
    price: int | None
    cancel_reason: str | None


class ClassifyFeedbackResult(TypedDict):
    is_feedback: bool
    nm_id: int | None
    cancel_reason: str | None


class ClassifyCutLabelsResult(TypedDict):
    is_cut_labels: bool
    cancel_reason: str | None


class AnswerResult(TypedDict):
    response: str
    wants_to_stop: bool
    switch_to_article_id: int | None


class PredialogResult(TypedDict):
    response: str
    article_ids: list[int]


class OpenAIGateway:
    def __init__(self, config: OpenAIConfig) -> None:
        self._client = AsyncOpenAI(
            api_key=config.openai_api_key,
            http_client=AsyncClient(proxy=config.proxy, transport=AsyncHTTPTransport(local_address="0.0.0.0")),
        )

    async def classify_order_screenshot(
        self,
        photo_url: str,
        articles: list[CashbackArticle],
    ) -> ClassifyOrderResult:
        """Классифицирует скриншот заказа по списку товаров."""
        articles_text = "\n".join(
            f'- nm_id={art.nm_id}, Название: "{art.title}", Бренд: "{art.brand_name}"'
            for art in articles
        )
        valid_nm_ids = {art.nm_id for art in articles}
        
        system_content = """
        Ты помощник для анализа скриншотов заказов Wildberries.
        
        Проанализируй скриншот заказа на Wildberries и определи:
        1. Есть ли на скриншоте ЗАКАЗ одного из целевых товаров (из списка ниже)
        2. Какой именно товар заказан (по nm_id)
        3. Какая цена указана для этого товара в рублях (₽)
        
        ВАЖНЫЕ признаки заказа на Wildberries:
        - Наличие слова "Заказы" в верхней части экрана
        - Рядом с карточкой товара есть статусы: "Оформляется", "Вы оформили заказ", "Оплачен" (зелёным), "НЕ ОПЛАЧЕН" (красным)
        - Карточка товара содержит изображение, название товара, бренд и цену
        
        Сравни изображение товара на скриншоте с эталонными изображениями товаров (если предоставлены).
        
        Верни ответ в формате JSON: {"is_order": bool, "nm_id": int|null, "price": int|null, "cancel_reason": str|null}
        Где:
        - is_order = true, если заказ одного из наших товаров присутствует на скриншоте
        - nm_id = артикул товара который найден на скриншоте, или null если товар не найден
        - price = цена товара в рублях, или null если цена не видна
        - cancel_reason = причина отказа, если is_order = false
        """
        
        prompt = f"""
        ЦЕЛЕВЫЕ ТОВАРЫ (ищем заказ ОДНОГО из них):
        {articles_text}
        """

        user_content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]

        for art in articles:
            if art.image_url:
                user_content.append({"type": "input_image", "image_url": art.image_url})

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        response = await self._client.responses.create(
            model=MODEL_NAME,
            input=messages,
            reasoning={"effort": GPT_REASONING},
            max_output_tokens=GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
            prompt_cache_key=_build_prompt_cache_key("classify_order_screenshot"),
            prompt_cache_retention="24h",
        )
        _log_response_usage("classify_order_screenshot", response)

        result = _extract_response_text(response)

        if not result:
            return {"is_order": False, "nm_id": None, "price": None, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            parsed = json.loads(result)
            logger.debug("classified order screenshot %s", parsed)
            if parsed.get("nm_id") and parsed["nm_id"] not in valid_nm_ids:
                parsed["nm_id"] = None
                parsed["is_order"] = False
            return parsed

        return {"is_order": False, "nm_id": None, "price": None, "cancel_reason": None}

    async def classify_feedback_screenshot(
        self,
        photo_url: str,
        articles: list[CashbackArticle],
    ) -> ClassifyFeedbackResult:
        """Классифицирует скриншот отзыва по списку товаров."""
        articles_text = "\n".join(
            f'- nm_id={art.nm_id}, Название: "{art.title}", Бренд: "{art.brand_name}"'
            for art in articles
        )
        valid_nm_ids = {art.nm_id for art in articles}
        
        system_content = """
        Ты помощник для анализа скриншотов отзывов Wildberries.
        
        Проанализируй скриншот и определи:
        1. Есть ли на скриншоте ОТЗЫВ на один из целевых товаров (из списка ниже)
        2. На какой именно товар оставлен отзыв (по nm_id)
        
        КРИТЕРИИ:
            - Подпись у товара должна быть названием целевого товара или его брендом.
            - На скриншоте клиента обязательно должны быть 5 оранжевых звёзд ⭐️. Звёзды могут быть прямо на фотографии товара.
            - ТЕКСТ у отзыва может отсутствовать.
            - ТЕКСТ отзыва(ЕСЛИ ОН ЕСТь) НЕ должен содержать описание товара. Только общие фразы МОГУТ БЫТЬ, например: "товар хороший", "всё хорошо", "отличный товар", и тд
            - На скриншоте НЕ должно быть замазок/блюра и других изменений, только обычный скриншот с телефона без исправлений
        
        Верни ответ в формате JSON: {"is_feedback": bool, "nm_id": int|null, "cancel_reason": str|null}
        Где:
        - is_feedback = true, если на скриншоте есть отзыв с 5 звёздами на один из наших товаров
        - nm_id = артикул товара на который оставлен отзыв, или null если не найден
        - cancel_reason = причина отказа, если is_feedback = false
        """
        
        prompt = f"""
        Подумай и скажи есть ли на скриншоте ОТЗЫВ на один из наших товаров на Wildberries, сделанный согласно нашим КРИТЕРИЯМ.

        ЦЕЛЕВЫЕ ТОВАРЫ (ищем отзыв на ОДИН из них):
        {articles_text}
        """

        user_content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]
        
        for art in articles:
            if art.image_url:
                user_content.append({"type": "input_image", "image_url": art.image_url})
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user","content": user_content},
        ]

        response = await self._client.responses.create(
            model=MODEL_NAME,
            input=messages,
            reasoning={"effort": GPT_REASONING},
            max_output_tokens=GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
            prompt_cache_key=_build_prompt_cache_key("classify_feedback_screenshot"),
            prompt_cache_retention="24h",
        )
        _log_response_usage("classify_feedback_screenshot", response)


        result = None
        for item in response.output:
            if getattr(item, "content", None):
                for block in item.content:
                    text = getattr(block, "text", None)
                    if text:
                        result = text.strip()
                        break

        if not result:
            return {"is_feedback": False, "nm_id": None, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            parsed = json.loads(result)
            logger.info("classified feedback screenshot %s", parsed)
            # Валидируем nm_id
            if parsed.get("nm_id") and parsed["nm_id"] not in valid_nm_ids:
                parsed["nm_id"] = None
                parsed["is_feedback"] = False
            return parsed

        return {"is_feedback": False, "nm_id": None, "cancel_reason": None}

    async def classify_cut_labels_photo(self, photo_url: str) -> ClassifyCutLabelsResult:
        system_content = """
        Ты помощник для анализа фотографий разрезанных этикеток Wildberries.
        """
        prompt = """
        Подумай и скажи есть ли на фотографии клиента РАЗРЕЗАННЫЕ/ПОРВАННЫЕ/ЗАМАЗАННЫЕ этикетки (штрихкода или QR-кода) Wildberries.

        Верни ответ в формате JSON: {"is_cut_labels": bool, "cancel_reason": str|null}
        Где is_cut_labels = true, если на фотографии есть РАЗРЕЗАННЫЕ/ПОРВАННЫЕ/ЗАМАЗАННЫЕ этикетки (штрихкода или QR-кода) Wildberries,
        cancel_reason = причина отказа, если is_cut_labels = false
        """

        user_content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        response = await self._client.responses.create(
            model=MODEL_NAME,
            input=messages,
            reasoning={"effort": GPT_REASONING},
            max_output_tokens=GPT_MAX_OUTPUT_TOKENS_PHOTO_ANALYSIS,
            prompt_cache_key=_build_prompt_cache_key("classify_cut_labels_photo"),
            prompt_cache_retention="24h",
        )
        _log_response_usage("classify_cut_labels_photo", response)

        result = _extract_response_text(response)

        if not result:
            return {"is_cut_labels": False, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.info("classified cut labels screenshot %s", result)
            return result

        return {"is_cut_labels": False, "cancel_reason": None}

    async def answer_user_question(
        self,
        user_message: str,
        articles: list[CashbackArticle],
        current_buyers: list[Buyer],
    ) -> AnswerResult:
        """Отвечает на вопрос пользователя в контексте кешбек-диалога."""
        articles_text = "\n".join([f"- ID:{article.id} Артикул WB: {article.nm_id}, Название: {article.title}" for article in articles])
        current_buyers_text = "\n".join(
            [
                f"- Артикул WB:{buyer.nm_id}, Скриншот заказа:{buyer.is_ordered} Скриншот отзыва:{buyer.is_left_feedback} Фото разрезанных этикеток:{buyer.is_left_feedback}"
                for buyer in current_buyers
            ]
        )

        instruction_text = articles[0].instruction_text

        system_content = """
        Ты — вежливый помощник кешбек-сервиса Wildberries.
        
        Процесс получения кешбека:
        1. Скриншот заказа — клиент отправляет скриншот оформленного заказа
        2. Скриншот отзыва — после получения товара клиент оставляет отзыв на 5 звёзд и присылает скриншот
        3. Фото разрезанных этикеток — клиент разрезает этикетки со штрихкодом/QR-кодом и присылает фото
        4. Реквизиты — клиент отправляет данные для перевода кешбека
        
        ВАЖНО:
        - Ответь кратко, по делу (не более 3-4 предложений) без смайликов и эмодзи
        - НЕ добавляй завершающие фразы типа "Если возникнут вопросы — помогу"
        - Используй разметку Markdown
        - НИКОГДА не показывай пользователю ID артикулов — только названия товаров
        - Если клиент спрашивает какие товары доступны — перечисли ТОЛЬКО названия из блока `articles_list` ниже.
        - Если клиент спрашивает фото или артикул товара или как ему найти товар, НЕ ГОВОРИ, что товар можно найти поиском по названию, переспроси,
           о каком товаре он спрашивает и перечисли ТОЛЬКО названия из блока `articles_list`
        - Если клиент спрашивает на каком он этапе или что ему нужно сделать, перечисли заявки из блока `buyers_list`
        
        СПЕЦИАЛЬНЫЕ КОМАНДЫ (добавляй в начало ответа если нужно):

        1. Если клиент ОДНОЗНАЧНО хочет прекратить процесс по текущему товару
           (например: "Не хочу", "Отмена", "Стоп", "Передумал", "Нет, спасибо", "Спасибо пока не нужно", "Спасибо, не надо","Не надо спасибо"),
           напиши [STOP] в начале ответа.

        2. Если пишет оскорбления, унижения, ругательства
           (например: "Пошел ты", "иди нахуй", "блять"),
           напиши [STOP] в начале ответа.
        
        3. Если пользователь просит начать оформление или упоминает товар,
           (например: "Давайте следующие пакеты", "Хочу ещё ролик", "Оформим диски", "Продолжаем, ножницы", "У меня же еще ножницы")
           которого НЕТ в `buyers_list`, но он ЕСТЬ в `articles_list`, ты должен начать ответ со специальной команды.
           напиши [SWITCH:ID] где ID — числовой идентификатор из `articles_list`.
           Пример: [SWITCH:123] Отлично, давайте оформим заявку на этот товар (БЕЗ упоминания ID после команды).
        
        Не путай вопросы или сомнения с командами — только явные намерения.
        """
        
        prompt = f"""
        ИНСТРУКЦИЯ, что и как нужно делать клиенту
        (МОЖЕШЬ  КРАТКО ПЕРЕСКАЗАТЬ КЛИЕНТУ, ЕСЛИ ОН НЕ ПОНИМАЕТ ЧТО ДЕЛАТЬ):
        {instruction_text}

        ДОСТУПНЫЕ ТОВАРЫ (`articles_list`):
        {articles_text}

        ТЕКУЩИЕ ЗАЯВКИ (`buyers_list`):
        {current_buyers_text}
        
        Новое сообщение клиента: "{user_message}"
        """

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]

        response = await self._client.responses.create(
            model=MODEL_NAME,
            input=messages,
            max_output_tokens=GPT_MAX_OUTPUT_TOKENS,
            prompt_cache_key=_build_prompt_cache_key("answer_user_question"),
            prompt_cache_retention="24h",
        )
        _log_response_usage("answer_user_question", response)

        result = _extract_response_text(response)
        return _parse_answer_result(result)

    async def chat_with_client(
        self,
        user_message: str,
        articles: list[CashbackArticle],
        chat_history: list[ChatHistoryEntry] | None = None,
        photo_url: str | None = None,
    ) -> PredialogResult:
        """Ведёт pre-dialog общение с клиентом до классификации артикула."""
        articles_info = "\n".join(f"- ID:{article.id} | Название: {article.title}" for article in articles)
        articles_titles = "\n".join(f"- {article.title}" for article in articles)
        valid_ids = {article.id for article in articles}

        history_text = ""
        if chat_history:
            history_lines = []
            for entry in chat_history[-10:]:
                history_lines.append(f"Клиент: {entry['user']}")
                history_lines.append(f"Ты: {entry['assistant']}")
            history_text = "\n".join(history_lines)

        # во тут вообще без понятия как в промпт передать конктретную инструкцию, поэтому передаю самую первую
        instructions = []
        for article in articles:
            instructions.append(article.instruction_text)
        first_instruction_text = instructions[0]
        
        system_content = """
        Ты — приветливый менеджер кешбек-сервиса на Wildberries. Твоя задача — помочь клиенту выбрать товар для кешбека.
        
        СТРОГИЕ ЗАПРЕТЫ:
        - НИКОГДА не давай ссылки на изображения или URL
        - НИКОГДА не угадывай товар — если непонятно, переспроси
        - НИКОГДА не показывай ID артикулов
        - НИКОГДА не придумывай информацию о товаре
        - НИКОГДА не говори пользователю как найти товар на маркетплейсе
        
        ПРАВИЛА ОБЩЕНИЯ:
        1. Отвечай кратко , по-деловому и четко (2-4 предложения) без смайликов и эмодзи
        2. Используй разметку Markdown
        3. НЕ добавляй формальные завершающие фразы
        
        ЛОГИКА ДИАЛОГА:
        - Если клиент просто здоровается или спрашивает "актуально?" — напиши "Напишите название товара, по которому хотите кэшбек" и перечисли доступные товары(БЕЗ ПРИЛАТЕЛЬНЫХ В НАЗВАНИИ ТОВАРА)
        - Если клиент спрашивает об условиях в общем — кратко скажи, что условия зависят от товара, и попроси уточнить название
        - Если клиент задаёт неопределённый вопрос ("это какое?", "фото можно?", "а что это?") — ПЕРЕСПРОСИ о каком именно товаре он спрашивает
        - Если клиент ЯВНО называет конкретный товар (например "ролик", "губки", "носки", "салфетка") — подтвердить выбор товара и ДОБАВЬ в начало ответа: [ARTICLE:ID]
        - Добавляй [ARTICLE:ID] ТОЛЬКО когда клиент ОДНОЗНАЧНО выбрал товар
        - Если клиент выбрал несколько товаров то перечисли их так [ARTICLE:ID1,ID2,ID3]
                
        ПРИМЕР 1 (неопределённый вопрос):
        Клиент: "это какое? фото можно?"
        Ответ: Уточните, пожалуйста, о каком товаре вы спрашиваете? У нас есть: Ролик , Губка, Салфетка
        
        ПРИМЕР 2 (явный выбор):
        Клиент: "ролик"
        Ответ: [ARTICLE:123]Отлично, заказывайте на сайте товар, артикул: [АРТИКУЛ_РОЛИКА_ИЗ_ARTICLE_TITLES]
        """
        
        prompt = f"""
        ИНСТРУКЦИЯ, что и как нужно делать клиенту
        (МОЖЕШЬ  КРАТКО ПЕРЕСКАЗАТЬ КЛИЕНТУ, ЕСЛИ ОН НЕ ПОНИМАЕТ ЧТО ДЕЛАТЬ):
        {first_instruction_text}
        
        Доступные товары для кешбека (ТОЛЬКО ДЛЯ СИСТЕМЫ, ID не показывать пользователю):
        {articles_info}

        Список товаров для показа пользователю:
        {articles_titles}
        (ПОКАЗЫВАЙ ТОЛЬКО НАЗВАНИЕ ТОВАРА, БЕЗ ПРИЛАГАТЕЛЬНЫХ, например: Диски ватные специальные -> Диски)
        
        {"История диалога:" + chr(10) + history_text if history_text else ""}

        Новое сообщение клиента: "{user_message}"
        """

        user_content: list[dict[str, str]] | str
        if photo_url:
            user_content = [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": photo_url},
            ]
        else:
            user_content = prompt

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

        response = await self._client.responses.create(
            model=MODEL_NAME,
            input=messages,
            max_output_tokens=GPT_MAX_OUTPUT_TOKENS,
            prompt_cache_key=_build_prompt_cache_key("chat_with_client"),
            prompt_cache_retention="24h",
        )
        _log_response_usage("chat_with_client", response)

        result = _extract_response_text(response)
        parsed = _parse_predialog_result(result)

        if parsed["article_ids"]:
            parsed["article_ids"] = [aid for aid in parsed["article_ids"] if aid in valid_ids]

        return parsed


def _extract_response_text(response: Response) -> str | None:
    """Извлекает текст ответа из response объекта OpenAI"""
    for item in response.output:
        if getattr(item, "content", None):
            for block in item.content:
                text = getattr(block, "text", None)
                if text:
                    return text.strip()
    return None


def _build_prompt_cache_key(scope: str) -> str:
    return f"axiomai:{scope}"


def _log_response_usage(operation: str, response: Response) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return

    cached_tokens = getattr(getattr(usage, "input_tokens_details", None), "cached_tokens", None)
    input_tokens = getattr(usage, "input_tokens", None)
    output_tokens = getattr(usage, "output_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)
    reasoning_tokens = getattr(getattr(usage, "output_tokens_details", None), "reasoning_tokens", None)

    non_cached_input_tokens = None
    if isinstance(input_tokens, int) and isinstance(cached_tokens, int):
        non_cached_input_tokens = max(input_tokens - cached_tokens, 0)

    visible_output_tokens = None
    if isinstance(output_tokens, int) and isinstance(reasoning_tokens, int):
        visible_output_tokens = max(output_tokens - reasoning_tokens, 0)

    logger.info(
        (
            "%s usage: input_tokens=%s, cached_tokens=%s, non_cached_input_tokens=%s, "
            "output_tokens=%s, reasoning_tokens=%s, visible_output_tokens=%s, total_tokens=%s"
        ),
        operation,
        input_tokens,
        cached_tokens,
        non_cached_input_tokens,
        output_tokens,
        reasoning_tokens,
        visible_output_tokens,
        total_tokens,
    )


def _parse_answer_result(result: str | None) -> AnswerResult:
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

    return AnswerResult(
        response=result,
        wants_to_stop=wants_to_stop,
        switch_to_article_id=switch_to_article_id,
    )


def _parse_predialog_result(result: str | None) -> PredialogResult:
    """Парсит результат pre-dialog ответа GPT и извлекает article_ids"""
    if not result:
        return PredialogResult(response="Напишите название товара, по которому хотите кэшбек", article_ids=[])

    article_ids: list[int] = []
    if "[ARTICLE:" in result:
        match = re.search(r"\[ARTICLE:([\d,]+)\]", result)
        if match:
            ids_str = match.group(1)
            article_ids = [int(id_str) for id_str in ids_str.split(",") if id_str]
            result = re.sub(r"\[ARTICLE:[\d,]+\]", "", result).strip()

    return PredialogResult(response=result, article_ids=article_ids)
