.PHONY: help setup seed pipeline api web test fmt clean

PY := backend/.venv/bin/python
UVICORN := backend/.venv/bin/uvicorn

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

setup: ## create venv + install backend (editable) and frontend deps
	cd backend && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -e ".[dev]"
	cd frontend && npm install

seed: ## regenerate synthetic Sikkim dataset -> backend/data/interim/
	cd backend && ../$(PY) -m redzone.seed.generate_sikkim

pipeline: ## run full analytics pipeline -> backend/data/processed/
	cd backend && ../$(PY) -m redzone.pipeline

api: ## serve FastAPI at :8000
	cd backend && ../$(UVICORN) redzone.api.main:app --reload --port 8000

web: ## serve Vite dev server at :5173
	cd frontend && npm run dev

test: ## run backend tests
	cd backend && ../$(PY) -m pytest -q

fmt: ## format backend
	cd backend && ../.venv/bin/ruff check --fix . && ../.venv/bin/ruff format .

clean: ## drop generated data
	rm -rf backend/data/interim/* backend/data/processed/*
