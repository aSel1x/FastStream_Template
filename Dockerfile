FROM ghcr.io/astral-sh/uv:latest as uv
FROM python:3.13-slim-bookworm as builder

COPY --from=uv /uv /uvx /bin/
COPY uv.lock pyproject.toml ./

RUN uv pip compile pyproject.toml -o requirements.prod.txt && \
    uv pip compile --group dev pyproject.toml -o requirements.dev.txt

FROM python:3.13-slim-bookworm as dev

WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder requirements.dev.txt /src

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip && pip install --no-cache-dir -r requirements.dev.txt

COPY ./src .