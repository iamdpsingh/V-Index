"""Account onboarding and owner-scoped job posting."""

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_, select, update

from vindex.accounts.models import Account, EmployerPosting
from vindex.accounts.security import principal, rate_limit, require_origin
from vindex.db import Observation, Session, Source, now
from vindex.ingest import ingest
from vindex.schemas import Enumeration, JobInput

router = APIRouter(prefix="/api/v1/me", tags=["Employer workspace"])
guard = [Depends(require_origin)]


class RoleSelection(BaseModel):
    role: Literal["candidate", "employer"]


class PostingInput(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    company: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=8000)
    location: str = Field(min_length=1, max_length=160)
    application_url: str = Field(max_length=2048)


def posting_owner(request, session) -> Account:
    user = principal(request, session)
    locked = session.scalar(select(Account).where(Account.id == user.id).with_for_update())
    if not locked or locked.role != "employer":
        raise HTTPException(403, "Choose an employer role to manage postings")
    return locked


def record(item: EmployerPosting) -> dict:
    return {**item.data, "id": item.id, "status": item.status}


@router.put("/role", dependencies=guard)
def set_role(body: RoleSelection, request: Request):
    with Session() as session:
        user = principal(request, session)
        rate_limit(f"account-role:{user.id}", 10)
        changed = session.execute(
            update(Account)
            .where(Account.id == user.id, or_(Account.role.is_(None), Account.role == body.role))
            .values(role=body.role)
            .returning(Account.id)
        )
        if changed.scalar_one_or_none() is None:
            raise HTTPException(409, "An account role has already been selected")
        session.commit()
    return body


@router.get("/postings")
def list_postings(request: Request):
    with Session() as session:
        owner = posting_owner(request, session)
        rows = session.scalars(
            select(EmployerPosting).where(EmployerPosting.account_id == owner.id)
        )
        return [record(row) for row in rows]


def save_posting(request: Request, body: PostingInput, posting_id: str | None) -> dict:
    fields = {key: value.strip() for key, value in body.model_dump().items()}
    if not all(fields.values()):
        raise HTTPException(422, "Complete all posting fields")
    try:
        JobInput(external_id="validation", source_url=fields["application_url"], **fields)
    except ValueError as error:
        raise HTTPException(422, "Use a valid HTTPS application link") from error
    with Session() as session:
        owner = posting_owner(request, session)
        rate_limit(f"employer-write:{owner.id}", 20)
        if posting_id:
            item = session.get(EmployerPosting, posting_id)
            if not item or item.account_id != owner.id:
                raise HTTPException(404, "Posting not found")
        else:
            item = EmployerPosting(id=str(uuid4()), account_id=owner.id, status="draft", data={})
            session.add(item)
        item.data = fields
        if item.status == "published":
            publish(session, item)
        session.commit()
        return record(item)


@router.post("/postings", status_code=201, dependencies=guard)
def create_posting(body: PostingInput, request: Request):
    return save_posting(request, body, None)


@router.put("/postings/{posting_id}", dependencies=guard)
def edit_posting(posting_id: str, body: PostingInput, request: Request):
    return save_posting(request, body, posting_id)


def publish(session, item: EmployerPosting) -> None:
    if not item.source_id:
        source = Source(
            provider="employer_posting",
            slug=item.id,
            company=item.data["company"],
            url=item.data["application_url"],
        )
        session.add(source)
        session.flush()
        item.source_id = source.id
    source = session.get(Source, item.source_id)
    assert source is not None
    ingest(
        session,
        source,
        Enumeration(
            complete=True,
            jobs=[
                JobInput(external_id=item.id, source_url=item.data["application_url"], **item.data)
            ],
        ),
    )


@router.post("/postings/{posting_id}/{action}", dependencies=guard)
def change_status(posting_id: str, action: Literal["publish", "close"], request: Request):
    with Session() as session:
        owner = posting_owner(request, session)
        rate_limit(f"employer-write:{owner.id}", 20)
        item = session.get(EmployerPosting, posting_id)
        if not item or item.account_id != owner.id:
            raise HTTPException(404, "Posting not found")
        if action == "publish":
            if not owner.email_verified_at:
                raise HTTPException(403, "Verify your email before publishing")
            publish(session, item)
            item.status = "published"
        else:
            if item.source_id:
                for observation in session.scalars(
                    select(Observation).where(Observation.source_id == item.source_id)
                ):
                    observation.status = "closed"
                    observation.last_checked = now()
            item.status = "closed"
        session.commit()
        return record(item)
