FROM python:3.12-slim

WORKDIR /code

RUN pip install poetry

COPY . /code/

RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi
