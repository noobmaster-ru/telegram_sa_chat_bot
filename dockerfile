FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

# 1. Сначала манифесты — чтобы кеш слоёв работал
COPY pyproject.toml uv.lock README.md ./

# 2. Синхронизируем зависимости по lock-файлу
#   (создаст .venv внутри контейнера)
RUN uv sync --frozen --no-dev

# 3. Копируем исходный код
COPY . .

# 4. Базовая команда (всё равно будет переопределена в docker-compose)
CMD ["uv", "run", "python", "run.py"]