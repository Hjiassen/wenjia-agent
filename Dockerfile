FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.5 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN python -m pip install --upgrade pip \
    && python -m pip install "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock README.md ./
COPY wenjia_agent ./wenjia_agent
COPY apps ./apps

RUN poetry install --only main --no-interaction --no-ansi

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin wenjia \
    && mkdir -p /data /app/logs \
    && chown -R wenjia:wenjia /data /app/logs

USER wenjia

EXPOSE 8000

CMD ["uvicorn", "apps.web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
