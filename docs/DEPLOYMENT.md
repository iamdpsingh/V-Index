# Deployment

Docker Compose is the intended production-like local path. Install Docker first. Copy `.env.example` to `.env` and choose a long ADMIN_TOKEN. Run `docker compose up --build -d`; migrate is a one-shot dependency. API: http://localhost:8000/docs. Web: http://localhost:3000. Database and Redis are internal only.

Local SQLite: `uv sync --frozen && uv run alembic upgrade head`; set PYTHONPATH=backend, ADMIN_TOKEN, optionally DATABASE_URL and REDIS_URL. Start API with uvicorn and worker with python -m vindex.worker. PostgreSQL URL format is postgresql+psycopg://user:password@host:5432/db. SQLite is for single-process development/tests, not concurrent production workers.

Before internet exposure add HTTPS, gateway request limits, secrets storage, network egress policy and backups. Compose is a single-host baseline, not a fully hardened deployment. Container/service execution must be tested where Docker is installed. Do not deploy the example credentials publicly.

The web container uses root-context Dockerfile.web so the repository .dockerignore excludes host node_modules and .next files. Compose uses this recipe; apps/web/Dockerfile is the original frontend scaffold recipe and is not selected by Compose. CI also builds and boots the full Compose stack, checks API/database health, Redis, migrations, the web page and API proxy. Read its actual run result before claiming deployment verification.

Full-stack baseline passed in CI on f4cf0ef: https://github.com/iamdpsingh/V-Index/actions/runs/42069063452. The web waits for API health; startup checks tolerate bounded TCP readiness resets. Live provider ingestion and hosted production operation are separate acceptance checks.
