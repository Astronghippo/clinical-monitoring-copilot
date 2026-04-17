FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg and pypdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install --system --no-cache \
    fastapi "uvicorn[standard]" \
    sqlalchemy "psycopg[binary]" alembic \
    pydantic pydantic-settings python-multipart \
    pypdf pandas anthropic

COPY . .

# Railway injects PORT. Default 8000 for local docker-compose.
ENV PORT=8000
EXPOSE 8000

# On startup: create DB tables if missing, then launch uvicorn.
# (Prototype shortcut — production would use alembic upgrade head.)
CMD ["sh", "-c", "python -c 'from app.db import Base, engine; from app import models; Base.metadata.create_all(engine)' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
