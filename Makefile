.PHONY: help
help:
	@echo "USAGE"
	@echo "  make <commands>"
	@echo ""
	@echo "AVAILABLE COMMANDS"
	@echo "  ref		Reformat code"
	@echo "  app		Start the application"
	@echo "  tests		Start the pytest tests"
	@echo "  docker		Docker container build"
	@echo "  migrate	Alembic migrate database"
	@echo "  generate	Alembic generate database"
	@echo "  req		pyproject.toml >> requirements.txt"


.PHONY: ref
ref:
	poetry run pre-commit run --all-files

.PHONY: app
app:
	set -a; source .env; set +a; \
	poetry run python -m app

.PHONY: tests
tests:
	set -a; source .env; source .env.tests; set +a; \
	poetry run pytest

.PHONY: docker
docker:
	docker-compose up -d --build

.PHONY: migrate
migrate:
	poetry run alembic upgrade head

.PHONY: generate
generate:
	poetry run alembic revision --autogenerate

.PHONY: req
req:
	@poetry export --without-hashes --without-urls | sed 's/;.*//' | tee requirements.txt
