import json
import logging
import re
from contextlib import suppress

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
from axiomai.infrastructure.database.models.cashback_table import CashbackArticle

logger = logging.getLogger(__name__)



class OpenAIGateway:
    def __init__(self, config: OpenAIConfig) -> None:
        self._client = AsyncOpenAI(
            api_key=config.openai_api_key,
            http_client=AsyncClient(proxy=config.proxy, transport=AsyncHTTPTransport(local_address="0.0.0.0")),
        )

    async def classify_order_screenshot(
        self, photo_url: str, article_title: str, brand_name: str, article_image_url: str | None = None
    ) -> dict[str, bool | str | int | None]:
        
        system_content = """
        Ты помощник для анализа скриншотов заказов Wildberries.
        
        Проанализируй скриншот заказа на Wildberries и определи:
        1. Есть ли на скриншоте ЗАКАЗ целевого товара
        2. Какая цена указана для этого товара в рублях (₽)
        
        ВАЖНЫЕ признаки заказа на Wildberries:
        - Наличие слова "Заказы" в верхней части экрана
        - Рядом с карточкой товара есть статусы: "Оформляется", "Вы оформили заказ", "Оплачен" (зелёным), "НЕ ОПЛАЧЕН" (красным)
        - Карточка товара содержит изображение, название товара, бренд и цену
        
        Сравни изображение товара на скриншоте с эталонным изображением товара (если предоставлено).
        Товары должны визуально совпадать.
        
        Верни ответ в формате JSON: {"is_order": bool, "price": int|null, "cancel_reason": str|null}
        Где is_order = true, если заказ нашего товара присутствует на скриншоте,
        price = цена товара в рублях, или null если цена не видна,
        cancel_reason = причина отказа, если is_order = false
        """
        
        prompt = f"""
        ЦЕЛЕВОЙ ТОВАР:
        - Название: "{article_title}"
        - Бренд: "{brand_name}"
        """

        user_content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]

        if article_image_url:
            user_content.append({"type": "input_image", "image_url": article_image_url})

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
            return {"is_order": False, "price": None, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.debug("classified order screenshot %s", result)
            return result

        return {"is_order": False, "price": None, "cancel_reason": None}

    async def classify_feedback_screenshot(
        self, photo_url: str, article_title: str, brand_name: str, article_image_url: str | None = None
    ) -> dict[str, bool | str | None]:
        
        system_content = """
        Ты помощник для анализа скриншотов отзывов Wildberries.
        
        КРИТЕРИИ:
            - Подпись у товара может быть названием целевого товара или его брендом.
            - На скриншоте клиента обязательно должны быть 5 оранжевых звёзд ⭐️. Звёзды могут быть прямо на фотографии товара.
            - Текст отзыва НЕ должен содержать описание товара. Только общие фразы МОГУТ БЫТЬ, например: "товар хороший", "всё хорошо", "отличный товар", и тд
            - На скриншоте НЕ должно быть замазок/блюра и других изменений, только обычный скриншот с телефона без исправлений
        
        Верни ответ в формате JSON: {"is_feedback": bool, "cancel_reason": str|null}
        Где is_feedback = true, если на скриншоте есть отзыв с 5 звёздами на наш товар, согласно нашим КРИТЕРИЯМ.
        cancel_reason = причина отказа, если is_feedback = false
        """
        
        prompt = f"""
        Подумай и скажи есть ли на скриншоте ОТЗЫВ на наш товар на Wildberries, сделанный согласно нашим КРИТЕРИЯМ.

        ЦЕЛЕВОЙ ТОВАР:
        - Название: "{article_title}"
        - Бренд: "{brand_name}"
        """

        user_content = [
            {"type": "input_text", "text": prompt},
            {"type": "input_image", "image_url": photo_url},
        ]
        if article_image_url:
            user_content.append({"type": "input_image", "image_url": article_image_url})
        
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
            return {"is_feedback": False, "cancel_reason": None}

        with suppress(json.JSONDecodeError, TypeError):
            result = json.loads(result)
            logger.info("classified feedback screenshot %s", result)
            return result

        return {"is_feedback": False, "cancel_reason": None}

    async def classify_cut_labels_photo(self, photo_url: str) -> dict[str, str | bool | None]:
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


        system_content = """
        Ты — вежливый помощник кешбек-сервиса Wildberries.
        
        Процесс получения кешбека:
        1. Скриншот заказа — клиент отправляет скриншот оформленного заказа
        2. Скриншот отзыва — после получения товара клиент оставляет отзыв на 5 звёзд и присылает скриншот
        3. Фото разрезанных этикеток — клиент разрезает этикетки со штрихкодом/QR-кодом и присылает фото
        4. Реквизиты — клиент отправляет данные для перевода кешбека
        
        ВАЖНО:
        - Ответь кратко, по делу (не более 3-4 предложений) без смайликов и эмодзи
        - Не повторяй ответы из истории диалога
        - НЕ добавляй завершающие фразы типа "Если возникнут вопросы — помогу"
        - Используй разметку Markdown
        - НИКОГДА не показывай пользователю ID артикулов — только названия товаров
        
        СПЕЦИАЛЬНЫЕ КОМАНДЫ (добавляй в начало ответа если нужно):

        1. Если клиент ОДНОЗНАЧНО хочет прекратить процесс по текущему товару
           (например: "Не хочу", "Отмена", "Стоп", "Передумал", "Нет, спасибо", "Спасибо пока не нужно", "Спасибо, не надо","Не надо спасибо"),
           напиши [STOP] в начале ответа.

        2. Если пишет оскорбления, унижения, ругательства
           (например: "Пошел ты", "иди нахуй", "блять"),
           напиши [STOP] в начале ответа.
        
        3. Если клиент хочет получить кешбек за ДРУГОЙ товар из списка доступных,
           напиши [SWITCH:ID] где ID — числовой идентификатор из списка выше.
           Например: [SWITCH:123]
           После этого напиши приветствие для нового артикула (БЕЗ упоминания ID).

        4. Если клиент спрашивает какие товары доступны — перечисли ТОЛЬКО названия из блока "ДОСТУПНЫЕ ТОВАРЫ ДЛЯ ПОЛЬЗОВАТЕЛЯ" ниже.
        
        Не путай вопросы или сомнения с командами — только явные намерения.
        """
        
        prompt = f"""
        КОНТЕКСТ:
        - Текущий товар: "{article_title}"
        - Текущий шаг: {current_step_desc}

        Инструкция выкупа для клиента:
        {instruction_text}

        {"Доступные артикулы (ТОЛЬКО ДЛЯ СИСТЕМЫ, ID не показывать пользователю):" + chr(10) + articles_text if articles_text else ""}

        {"ДОСТУПНЫЕ ТОВАРЫ ДЛЯ ПОЛЬЗОВАТЕЛЯ:" + chr(10) + articles_for_user if articles_for_user else ""}

        {"История диалога с клиентом:" + chr(10) + history_text if history_text else ""}

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
        chat_history: list[dict[str, str]] | None = None,
        photo_url: str | None = None,
    ) -> dict[str, str | int | None]:
        """
        Ведёт pre-dialog общение с клиентом до классификации артикула.

        Returns:
            dict с ключами:
            - response: str - текст ответа
            - article_id: int | None - ID артикула если GPT определил товар
        """
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


        system_content = """
        Ты — приветливый менеджер кешбек-сервиса на Wildberries. Твоя задача — помочь клиенту выбрать товар для кешбека.
        
        СТРОГИЕ ЗАПРЕТЫ:
        - НИКОГДА не давай ссылки на изображения или URL
        - НИКОГДА не угадывай товар — если непонятно, переспроси
        - НИКОГДА не показывай ID артикулов
        - НИКОГДА не придумывай информацию о товаре
        
        ПРАВИЛА ОБЩЕНИЯ:
        1. Отвечай кратко по-деловому и четко (2-4 предложения) без смайликов и эмодзи
        2. Используй разметку Markdown
        3. НЕ добавляй формальные завершающие фразы
        
        ЛОГИКА ДИАЛОГА:
        - Если клиент просто здоровается или спрашивает "актуально?" — напиши "Напишите название товара, по которому хотите кэшбек" и перечисли доступные товары
        - Если клиент спрашивает об условиях в общем — кратко скажи, что условия зависят от товара, и попроси уточнить название
        - Если клиент задаёт неопределённый вопрос ("это какое?", "фото можно?", "а что это?") — ПЕРЕСПРОСИ о каком именно товаре он спрашивает
        - Если клиент ЯВНО называет конкретный товар (например "ролик", "губки", "носки", "салфетка") — подтвердить выбор товара и ДОБАВЬ в начало ответа: [ARTICLE:ID]
        - Добавляй [ARTICLE:ID] ТОЛЬКО когда клиент ОДНОЗНАЧНО выбрал товар
        
        ПРИМЕР 1 (неопределённый вопрос):
        Клиент: "это какое? фото можно?"
        Ответ: Уточните, пожалуйста, о каком товаре вы спрашиваете? У нас есть: Ролик для одежды, Губка для Фитолампы.
        
        ПРИМЕР 2 (явный выбор):
        Клиент: "ролик"
        Ответ: [ARTICLE:123]Отлично, оформляем кешбек по этому товару. Дальше пришлю точные шаги.
        """
        
        prompt = f"""
        Доступные товары для кешбека (ТОЛЬКО ДЛЯ СИСТЕМЫ, ID не показывать пользователю):
        {articles_info}

        Список товаров для показа пользователю:
        {articles_titles}

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

        if parsed["article_id"] and parsed["article_id"] not in valid_ids:
            parsed["article_id"] = None

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


def _parse_predialog_result(result: str | None) -> dict[str, str | int | None]:
    """Парсит результат pre-dialog ответа GPT и извлекает article_id"""
    if not result:
        return {"response": "Напишите название товара, по которому хотите кэшбек", "article_id": None}

    article_id = None
    if "[ARTICLE:" in result:
        match = re.search(r"\[ARTICLE:(\d+)\]", result)
        if match:
            article_id = int(match.group(1))
            result = re.sub(r"\[ARTICLE:\d+\]", "", result).strip()

    return {"response": result, "article_id": article_id}
