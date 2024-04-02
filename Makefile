test:
	docker compose exec api python -m pytest

check-lint:
	ruff check . 
	black --check .
	mypy --check .

format:
	ruff check --fix
	black .


github-actions:
	ruff check --output-format=github .
	black --check .
	mypy --check .
