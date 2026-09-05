FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.14-slim-bookworm AS builder

COPY --from=uv /uv /uvx /bin/
COPY uv.lock pyproject.toml ./

# `uv export` reads uv.lock, so the image installs exactly the resolved versions the repo is
# tested against. `uv pip compile` would re-resolve and silently ignore the lockfile.
RUN uv export --frozen --no-dev --no-emit-project -o requirements.prod.txt && \
    uv export --frozen --no-emit-project -o requirements.dev.txt

FROM python:3.14-slim-bookworm AS dev

WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder requirements.dev.txt /src

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/* && \
    pip install --upgrade pip && pip install --no-cache-dir -r requirements.dev.txt && \
    useradd --create-home --uid 1000 app && chown -R app:app /src

COPY --chown=app:app ./src .

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/live', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "presentation.http.app:get_litestar", "--factory", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM python:3.14-slim-bookworm AS prod

WORKDIR /src

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder requirements.prod.txt /src

RUN pip install --no-cache-dir -r requirements.prod.txt && \
    useradd --create-home --uid 1000 app && chown -R app:app /src

COPY --chown=app:app ./src .

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health/live', timeout=4).status == 200 else 1)"

CMD ["uvicorn", "presentation.http.app:get_litestar", "--factory", "--host", "0.0.0.0", "--port", "8000"]
