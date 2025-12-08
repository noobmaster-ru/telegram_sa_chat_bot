FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app


COPY pyproject.toml README.md ./

RUN uv sync --no-dev


COPY . .

CMD ["uv", "run", "python", "run.py"]