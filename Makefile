# Docker Compose V1 (`docker-compose`) has been EOL since July 2023 and ships with nothing
# current. Override if you are still on it: `make COMPOSE=docker-compose build`.
COMPOSE ?= docker compose

.PHONY: help
help:
	@echo "USAGE"
	@echo "  make <commands>"
	@echo ""
	@echo "AVAILABLE COMMANDS"
	@echo "  build            Build and start all services (API + Queue + RabbitMQ + Postgres)"
	@echo "  start              Start all services (API + Queue + RabbitMQ + Postgres)"
	@echo "  restart          Restart all docker containers"
	@echo "  stop             Stop all docker containers"
	@echo "  logs-api         Show API logs"
	@echo "  logs-queue       Show Queue consumer logs"
	@echo "  logs-outbox      Show Outbox worker logs"
	@echo "  logs-rabbitmq    Show RabbitMQ logs"
	@echo "  logs-redis       Show Redis logs"
	@echo "  logs-hydra       Show Ory Hydra logs"
	@echo "  rabbitmq-ui      Open RabbitMQ management UI"
	@echo "  migration        Create alembic database migration"
	@echo "  migrate          Apply migrations up to head"
	@echo ""
	@echo "  test             Run the test suite"
	@echo "  cov              Run the test suite with a coverage report"
	@echo "  lint             Lint with ruff"
	@echo "  format           Format with ruff"
	@echo "  typecheck        Type-check with basedpyright"
	@echo "  layers           Check the dependency rule with import-linter"
	@echo "  check            lint + format check + typecheck + test (what CI runs)"


export PYTHONPATH=src
ifneq (,$(wildcard .env))
	include .env
	export $(shell sed 's/=.*//' .env)
endif


.PHONY: build
build:
	$(COMPOSE) up -d --build

.PHONY: start
start:
	$(COMPOSE) start

.PHONY: restart
restart:
	$(COMPOSE) stop && $(COMPOSE) start

.PHONY: stop
stop:
	$(COMPOSE) stop

.PHONY: logs-api
logs-api:
	$(COMPOSE) logs -f api

.PHONY: logs-queue
logs-queue:
	$(COMPOSE) logs -f queue

.PHONY: logs-outbox
logs-outbox:
	$(COMPOSE) logs -f outbox_worker

.PHONY: logs-rabbitmq
logs-rabbitmq:
	$(COMPOSE) logs -f rabbitmq

.PHONY: logs-redis
logs-redis:
	$(COMPOSE) logs -f redis

.PHONY: logs-hydra
logs-hydra:
	$(COMPOSE) logs -f hydra

.PHONY: rabbitmq-ui
rabbitmq-ui:
	@echo "Opening RabbitMQ Management UI at http://localhost:15672"
	@echo "Default credentials: guest / guest"
	@open http://localhost:15672 2>/dev/null || xdg-open http://localhost:15672 2>/dev/null || echo "Please open http://localhost:15672 manually"

.PHONY: migration
migration:
	POSTGRES_HOST=localhost uv run alembic -c alembic.ini revision --autogenerate

.PHONY: migrate
migrate:
	POSTGRES_HOST=localhost uv run alembic -c alembic.ini upgrade head

.PHONY: test
test:
	uv run pytest tests

.PHONY: cov
cov:
	uv run pytest tests --cov --cov-report=term-missing

.PHONY: lint
lint:
	uv run ruff check .

.PHONY: format
format:
	uv run ruff format .
	uv run ruff check --fix .

.PHONY: typecheck
typecheck:
	uv run basedpyright

.PHONY: layers
layers:
	uv run lint-imports

.PHONY: check
check:
	uv run ruff check .
	uv run ruff format --check .
	uv run lint-imports
	uv run basedpyright
	uv run pytest tests
