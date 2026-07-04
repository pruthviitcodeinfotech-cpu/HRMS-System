.PHONY: install run worker migrate revision test lint format

install:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	python -m app.jobs.worker

migrate:
	alembic upgrade head

revision:
	alembic revision --autogenerate -m "$(m)"

test:
	pytest

lint:
	ruff check app tests
	mypy app

format:
	black app tests
	ruff check --fix app tests
