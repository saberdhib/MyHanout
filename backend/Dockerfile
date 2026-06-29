# Backend FastAPI + Celery. Image légère ; le forecasting lourd (prophet/lgbm)
# est optionnel et n'est pas installé par défaut pour garder l'image rapide.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances système minimales (asyncpg/bcrypt/pypdf).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances d'abord (cache Docker).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[dev]"

# Copier le code.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
