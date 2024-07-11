.PHONY: help
help:
	@echo "USAGE"
	@echo "  make <commands>"
	@echo ""
	@echo "AVAILABLE COMMANDS"
	@echo "  ref		Reformat code"
	@echo "  amqp		Start the AMQP"
	@echo "  http		Start the HTTP"
	@echo "  run		Start the app"
	@echo "  docker		Docker container build"
	@echo "  migrate	Alembic migrate database"
	@echo "  generate	Alembic generate database"
	@echo "  req		pyproject.toml >> requirements.txt"


.PHONY: ref
ref: poetry run pre-commit run --all-files

.PHONY: amqp
amqp:
	faststream run --factory app:get_faststream_app --reload

.PHONY: http
http:
	uvicorn --factory app:get_litestar_app --reload

.PHONY: run
run:
	uvicorn --factory app:get_app --reload

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
