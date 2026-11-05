import hmac
import json
import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from vindex.connectors.public import detect
from vindex.db import Job, Observation, Run, Session, Source, now
from vindex.schemas import RunOut, SearchOut, SourceCreate, SourceOut

app = FastAPI(title="V-Index", version="0.1.0")


def admin(authorization: Annotated[str | None, Header()] = None):
    token = os.getenv("ADMIN_TOKEN")
    if not token:
        raise HTTPException(503, "Source management disabled: configure ADMIN_TOKEN")
    if not hmac.compare_digest(authorization or "", f"Bearer {token}"):
        raise HTTPException(401, "Invalid admin token")


def row(value):
    return {c.name: getattr(value, c.name) for c in value.__table__.columns}


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


@app.get("/api/v1/jobs", response_model=SearchOut)
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
                    "first_seen_at": j.first_seen,
                    "last_changed_at": j.last_changed,
                    "sources": [
                        {
                            "source_id": o.source_id,
                            "source_url": o.data["source_url"],
                            "application_url": o.data["application_url"],
                            "status": o.status,
                            "last_checked_at": o.last_checked,
                        }
                        for o in observations
                        if o.job_id == j.id
                    ],
                }
                for j in selected
            ],
        }


@app.get("/api/v1/jobs/{job_id}")
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
            "first_seen_at": job.first_seen,
            "last_changed_at": job.last_changed,
            "sources": [row(o) for o in observations],
        }
