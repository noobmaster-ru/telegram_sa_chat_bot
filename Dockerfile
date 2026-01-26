FROM python:3.13-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_PATH="/app"

ENV VIRTUAL_ENV="$APP_PATH/.venv"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR $APP_PATH

FROM python-base AS builder-base

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl git \
    && rm -rf /var/lib/apt/lists

RUN pip install --no-cache-dir uv

COPY ./pyproject.toml ./uv.lock ./

RUN uv venv \
    && uv sync --no-install-project

COPY ./alembic.ini ./
COPY ./axiomai ./axiomai

FROM python-base

COPY --from=builder-base $APP_PATH $APP_PATH
