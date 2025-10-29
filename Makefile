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
	@echo "  logs-rabbitmq    Show RabbitMQ logs"
	@echo "  rabbitmq-ui      Open RabbitMQ management UI"
	@echo "  migration        Create alembic database migration"


export PYTHONPATH=src
ifneq (,$(wildcard .env))
	include .env
	export $(shell sed 's/=.*//' .env)
endif


.PHONY: build
build:
	docker-compose up -d --build

.PHONY: start
start:
	docker-compose start

.PHONY: restart
restart:
	docker-compose stop && docker-compose start

.PHONY: stop
stop:
	docker-compose stop

.PHONY: logs-api
logs-api:
	docker-compose logs -f api

.PHONY: logs-queue
logs-queue:
	docker-compose logs -f queue

.PHONY: logs-rabbitmq
logs-rabbitmq:
	docker-compose logs -f rabbitmq

.PHONY: rabbitmq-ui
rabbitmq-ui:
	@echo "Opening RabbitMQ Management UI at http://localhost:15672"
	@echo "Default credentials: guest / guest"
	@open http://localhost:15672 2>/dev/null || xdg-open http://localhost:15672 2>/dev/null || echo "Please open http://localhost:15672 manually"

.PHONY: migration
migration:
	cd src && POSTGRES_HOST=localhost uv run alembic -c ../alembic.ini revision --autogenerate
