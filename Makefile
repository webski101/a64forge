.PHONY: install test lint typecheck frontend serve

install:
	python -m pip install -e ".[dev]"
	cd frontend && npm install

test:
	pytest -q

lint:
	ruff check .
	cd frontend && npm run lint

typecheck:
	mypy a64forge
	cd frontend && npm run typecheck

frontend:
	cd frontend && npm run build

serve:
	a64forge serve

