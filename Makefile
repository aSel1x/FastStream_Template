.PHONY: help
help:
	@echo "USAGE"
	@echo "  make <commands>"
	@echo ""
	@echo "AVAILABLE COMMANDS"
	@echo "  ref		Reformat code"
	@echo "  app		Start the application"
	@echo "  docker		Docker container build"
	@echo "  migrate	Alembic migrate database"
	@echo "  generate	Alembic generate database"
	@echo "  req		pyproject.toml >> requirements.txt"


.PHONY: ref
ref:
	poetry run pre-commit run --all-files

.PHONY: app
app:
	poetry run python -m app

.PHONY: docker
docker:
	docker-compose up -d

.PHONY: migrate
migrate:
	poetry run alembic upgrade head

.PHONY: generate
generate:
	poetry run alembic revision --autogenerate

.PHONY: req
req:
	@poetry export --without-hashes --without-urls | sed 's/;.*//' | tee requirements.txt
