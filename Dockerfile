# Сборка фронтенда
FROM node:20-alpine AS front
WORKDIR /f
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend .
RUN npm run build

# Бэкенд + собранный фронтенд; один образ для api, bot и migrate
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/alembic.ini .
COPY backend/alembic alembic
COPY backend/app app
COPY --from=front /f/dist static
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
