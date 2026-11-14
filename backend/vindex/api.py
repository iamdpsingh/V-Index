import hmac
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from vindex.accounts.api import router as account_router
from vindex.accounts.email_verification import recovery_router
from vindex.accounts.email_verification import router as email_verification_router
from vindex.accounts.middleware import PRIVATE_PREFIXES, PrivateRequestMiddleware
from vindex.accounts.oauth import router as oauth_router
from vindex.accounts.postings import router as posting_router
from vindex.accounts.profile_photo import router as profile_photo_router
from vindex.accounts.recommendations import router as recommendations_router
from vindex.accounts.resume_api import router as resume_router
from vindex.accounts.security import rate_limit
from vindex.connectors.registry import detect
from vindex.db import Job, Observation, Run, Session, Source, now
from vindex.ingest import aware
from vindex.plans import router as plans_router
from vindex.schemas import JobOut, RunOut, SearchOut, SourceCreate, SourceOut

app = FastAPI(
    title="Rolewisp API", version="0.1.0", docs_url=None, redoc_url=None, openapi_url=None
)
app.add_middleware(PrivateRequestMiddleware)
app.include_router(account_router)
app.include_router(oauth_router)
app.include_router(posting_router)
app.include_router(profile_photo_router)
app.include_router(email_verification_router)
app.include_router(recovery_router)
app.include_router(recommendations_router)
app.include_router(resume_router)
app.include_router(plans_router)


@app.middleware("http")
async def fresh_api_responses(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/") or request.url.path == "/health":
        # Polling must read the current index, not a browser/CDN snapshot.
        # Private middleware retains its additional cookie/security headers.
        response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(RequestValidationError)
async def redact_private_validation(request: Request, error: RequestValidationError):
    if request.url.path.startswith(PRIVATE_PREFIXES):
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
                    for item in error.errors()
                ]
            },
        )
    return await request_validation_exception_handler(request, error)


def admin(authorization: Annotated[str | None, Header()] = None):
    token = os.getenv("ADMIN_TOKEN")
    if not token:
        raise HTTPException(503, "Source management is temporarily unavailable")
    if not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(401, "Invalid admin token")


def row(value):
    values = {c.name: getattr(value, c.name) for c in value.__table__.columns}
    # Bookkeeping timestamps are written in UTC; SQLite does not retain tzinfo.
    # Original source dates stored inside JSON observations remain unchanged.
    return {
        key: aware(item).astimezone(UTC) if isinstance(item, datetime) else item
        for key, item in values.items()
    }


@app.get("/health")
def health():
    with Session() as session:
        session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/v1/providers")
def providers():
    return json.loads((Path(__file__).parents[1] / "providers.json").read_text())


@app.post(
    "/api/v1/sources", status_code=201, response_model=SourceOut, dependencies=[Depends(admin)]
)
def create_source(body: SourceCreate):
    try:
        provider, slug = detect(body.url)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    with Session() as session:
        source = Source(provider=provider, slug=slug, **body.model_dump())
        session.add(source)
        try:
            session.commit()
        except IntegrityError as e:
            session.rollback()
            raise HTTPException(409, "Board already registered") from e
        return row(source)


@app.get("/api/v1/sources", response_model=list[SourceOut], dependencies=[Depends(admin)])
def sources():
    with Session() as session:
        return [row(s) for s in session.scalars(select(Source).order_by(Source.id))]


@app.post("/api/v1/sources/{source_id}/refresh", status_code=202, dependencies=[Depends(admin)])
def request_refresh(source_id: int):
    with Session() as session:
        source = session.get(Source, source_id)
        if source is None:
            raise HTTPException(404, "Source not found")
        source.next_check = now()
        session.commit()
    return {"status": "scheduled", "source_id": source_id}


@app.get("/api/v1/runs", response_model=list[RunOut], dependencies=[Depends(admin)])
def runs(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    with Session() as session:
        return [
            row(r)
            for r in session.scalars(
                select(Run).order_by(Run.id.desc()).offset(offset).limit(limit)
            )
        ]


def limit_public_jobs(request: Request) -> None:
    if os.getenv("PUBLIC_JOB_RATE_LIMIT_ENABLED", "false") == "true":
        peer = request.client.host if request.client else "unknown"
        rate_limit(f"public-jobs:{peer}", 120)


@app.get("/api/v1/jobs", response_model=SearchOut, dependencies=[Depends(limit_public_jobs)])
def jobs(
    keyword: str = Query("", max_length=200),
    company: str = Query("", max_length=200),
    location: str = Query("", max_length=200),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    with Session() as session:
        active = select(Observation.job_id).where(Observation.status == "open")
        stmt = select(Job).where(Job.id.in_(active))
        for key, value in (("company", company), ("location", location)):
            if value:
                stmt = stmt.where(Job.data[key].as_string().icontains(value, autoescape=True))
        if keyword:
            stmt = stmt.where(
                (Job.data["title"].as_string().icontains(keyword, autoescape=True))
                | (Job.data["description"].as_string().icontains(keyword, autoescape=True))
            )
        total = session.scalar(select(func.count()).select_from(stmt.subquery()))
        selected = list(session.scalars(stmt.order_by(Job.id.desc()).offset(offset).limit(limit)))
        observations = (
            list(
                session.scalars(
                    select(Observation).where(Observation.job_id.in_([j.id for j in selected]))
                )
            )
            if selected
            else []
        )
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": j.id,
                    **j.data,
                    "raw": None,
                    "first_seen_at": aware(j.first_seen).astimezone(UTC),
                    "last_changed_at": aware(j.last_changed).astimezone(UTC),
                    "sources": [
                        {
                            "source_id": o.source_id,
                            "source_url": o.data["source_url"],
                            "application_url": o.data["application_url"],
                            "status": o.status,
                            "last_checked_at": aware(o.last_checked).astimezone(UTC),
                        }
                        for o in observations
                        if o.job_id == j.id
                    ],
                }
                for j in selected
            ],
        }


@app.get("/api/v1/jobs/{job_id}", response_model=JobOut, dependencies=[Depends(limit_public_jobs)])
def job_detail(job_id: int):
    with Session() as session:
        job = session.get(Job, job_id)
        if job is None:
            raise HTTPException(404, "Job not found")
        observations = list(
            session.scalars(select(Observation).where(Observation.job_id == job_id))
        )
        return {
            "id": job.id,
            **job.data,
            "first_seen_at": aware(job.first_seen).astimezone(UTC),
            "last_changed_at": aware(job.last_changed).astimezone(UTC),
            "sources": [
                {
                    "source_id": o.source_id,
                    "source_url": o.data["source_url"],
                    "application_url": o.data["application_url"],
                    "status": o.status,
                    "last_checked_at": aware(o.last_checked).astimezone(UTC),
                }
                for o in observations
            ],
        }
