# Deployment

Docker Compose is the intended production-like local path. Install Docker first. Copy `.env.example` to `.env` and choose a long ADMIN_TOKEN. Run `docker compose up --build -d`; migrate is a one-shot dependency. API: http://localhost:8000/docs. Web: http://localhost:3000. Database and Redis are internal only.

Local SQLite: `uv sync --frozen && uv run alembic upgrade head`; set PYTHONPATH=backend, ADMIN_TOKEN, optionally DATABASE_URL and REDIS_URL. Start API with uvicorn and worker with python -m vindex.worker. PostgreSQL URL format is postgresql+psycopg://user:password@host:5432/db. SQLite is for single-process development/tests, not concurrent production workers.

Before internet exposure add HTTPS, gateway request limits, secrets storage, network egress policy and backups. Compose is a single-host baseline, not a fully hardened deployment. Container/service execution must be tested where Docker is installed. Do not deploy the example credentials publicly.
