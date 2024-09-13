.PHONY: help
help:
	@echo "USAGE"
	@echo "  make <commands>"
	@echo ""
	@echo "AVAILABLE COMMANDS"
	@echo "  ref		        Reformat code"
	@echo "  http		        Start the HTTP app"
	@echo "  amqp		        Start the AMQP app"
	@echo "  scheduler	        Start the Scheduler app"
	@echo "  tests		        Start the pytest tests"
	@echo "  docker		        Docker container build"
	@echo "  docker-tests		Tests docker container build"
	@echo "  migrate	        Alembic migrate database"
	@echo "  generate	        Alembic generate database"
	@echo "  req		        pyproject.toml >> requirements.txt"


.PHONY: ref
ref:
	poetry run pre-commit run --all-files

.PHONY: http
http:
	set -a; source .env; set +a; \
	poetry run uvicorn app:http --reload

.PHONY: amqp
amqp:
	set -a; source .env; set +a; \
	poetry run faststream run app:amqp --reload

.PHONY: scheduler
scheduler:
	set -a; source .env; set +a; \
	poetry run taskiq scheduler app:scheduler

.PHONY: tests
tests:
	set -a; source .env; source .env.tests; set +a; \
	poetry run pytest

.PHONY: docker
docker:
	docker-compose up -d --build

.PHONY: docker-tests
docker-tests:
	docker-compose -f docker-compose-tests.yaml up --exit-code-from tests

.PHONY: migrate
migrate:
	poetry run alembic upgrade head

.PHONY: generate
generate:
	poetry run alembic revision --autogenerate

.PHONY: req
req:
	@poetry export --without-hashes --without-urls | sed 's/;.*//' | tee requirements.txt
