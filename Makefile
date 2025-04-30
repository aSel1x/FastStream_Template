.PHONY: help
help:
	@echo "USAGE"
	@echo "  make <commands>"
	@echo ""
	@echo "AVAILABLE COMMANDS"
	@echo "  ref		        Reformat code"
	@echo "  http		        Start the HTTP app"
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
	poetry run uvicorn --factory presentation.api:get_litestar --reload

.PHONY: docker
docker:
	docker-compose up -d --build

.PHONY: migrate
migrate:
	set -a; source .env; set +a; \
	poetry run alembic upgrade head

.PHONY: generate
generate:
	set -a; source .env; set +a; \
	poetry run alembic revision --autogenerate

.PHONY: req
req:
	@poetry export --without-hashes --without-urls | sed 's/;.*//' | tee requirements.txt
