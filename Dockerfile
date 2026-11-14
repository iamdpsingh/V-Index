FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend backend
COPY alembic.ini ./
ENV PYTHONPATH=/app/backend
RUN useradd --create-home vindex
USER vindex
CMD ["/app/.venv/bin/uvicorn", "vindex.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
