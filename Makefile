# Локальная разработка (SQLite). Перед первым запуском: make install
PY = backend/.venv/bin

install:
	python3.12 -m venv backend/.venv
	$(PY)/pip install -r backend/requirements-dev.txt
	cd frontend && npm install

migrate:
	cd backend && .venv/bin/alembic upgrade head

api:       ## API на :8000 (с BOT_IN_API=true — вместе с ботом)
	cd backend && .venv/bin/uvicorn app.api.main:app --reload

bot:       ## бот отдельным процессом
	cd backend && .venv/bin/python -m app.bot

front:     ## сайт на :5173, /api проксируется на :8000
	cd frontend && npm run dev

test:
	cd backend && .venv/bin/pytest -q

.PHONY: install migrate api bot front test
