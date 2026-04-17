FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml ./
RUN uv pip install --system fastapi "uvicorn[standard]" sqlalchemy "psycopg[binary]" alembic pydantic pydantic-settings python-multipart pypdf pandas anthropic pytest pytest-asyncio httpx
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
