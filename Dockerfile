FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.14-slim-bookworm AS builder

COPY --from=uv /uv /uvx /bin/
COPY uv.lock pyproject.toml ./

RUN uv pip compile pyproject.toml -o requirements.prod.txt && \
    uv pip compile --group dev pyproject.toml -o requirements.dev.txt

FROM python:3.14-slim-bookworm AS dev

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

CMD ["uvicorn", "presentation.http.app:get_litestar", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM python:3.14-slim-bookworm AS prod

WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder requirements.prod.txt /src

RUN pip install --no-cache-dir -r requirements.prod.txt

COPY ./src .

CMD ["uvicorn", "presentation.http.app:get_litestar", "--factory", "--host", "0.0.0.0", "--port", "8000"]
