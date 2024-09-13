FROM python:3.12

WORKDIR /app

RUN pip install poetry

COPY . /app/

RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi
