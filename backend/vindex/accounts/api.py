import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from vindex.accounts.models import (
    Account,
    AccountSession,
    EmployerPosting,
    OAuthIdentity,
    Profile,
    Resume,
)
from vindex.accounts.schemas import (
    AccountOut,
    Credentials,
    PasswordConfirmation,
    ProfileInput,
    ProfileOut,
    Registration,
)
from vindex.accounts.security import (
    DUMMY_HASH,
    clear_cookie,
    cookie_name,
    credential_rate,
    issue_session,
    passwords,
    principal,
    rate_limit,
    require_origin,
    token_digest,
)
from vindex.db import Observation, Session, now

router = APIRouter(prefix="/api/v1", tags=["Private accounts"])
write_guard = [Depends(require_origin)]


def account_data(account: Account) -> dict:
    return {
        "id": account.id,
        "email": account.email,
        "role": account.role,
        "email_verified": account.email_verified_at is not None,
        "created_at": account.created_at,
    }


@router.post("/auth/register", status_code=201, response_model=AccountOut, dependencies=write_guard)
def register(body: Registration, request: Request, response: Response):
    if os.getenv("ACCOUNT_REGISTRATION_ENABLED", "false").lower() != "true":
        raise HTTPException(503, "Registration is not enabled")
    email = str(body.email).casefold()
    credential_rate(request, email, signup=True)
    hashed = passwords.hash(body.password.get_secret_value())
    with Session() as session:
        account = Account(email=email, password_hash=hashed)
        session.add(account)
        try:
            session.flush()
            session.add(Profile(account_id=account.id, data=ProfileInput().model_dump()))
            issue_session(session, account, request, response)
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(409, "Unable to register with these account details") from error
        return account_data(account)


@router.post("/auth/login", response_model=AccountOut, dependencies=write_guard)
def login(body: Credentials, request: Request, response: Response):
    from sqlalchemy import select

    email = str(body.email).casefold()
    credential_rate(request, email)
    with Session() as session:
        account = session.scalar(select(Account).where(Account.email == email))
        valid = passwords.verify(
            body.password.get_secret_value(), account.password_hash if account else DUMMY_HASH
        )
        if not valid or account is None:
            raise HTTPException(401, "Invalid email or password")
        issue_session(session, account, request, response)
        session.commit()
        return account_data(account)


@router.post("/auth/logout", status_code=204, dependencies=write_guard)
def logout(request: Request, response: Response):
    token = request.cookies.get(cookie_name(), "")
    with Session() as session:
        session.execute(
            delete(AccountSession).where(AccountSession.token_hash == token_digest(token))
        )
        session.commit()
    clear_cookie(response)


@router.get("/me", response_model=AccountOut)
def me(request: Request):
    with Session() as session:
        return account_data(principal(request, session))


@router.get("/me/profile", response_model=ProfileOut)
def profile(request: Request):
    with Session() as session:
        user = principal(request, session)
        saved = session.get(Profile, user.id)
        return {**(saved.data if saved else {}), "updated_at": saved.updated_at if saved else None}


@router.put("/me/profile", response_model=ProfileOut, dependencies=write_guard)
def save_profile(body: ProfileInput, request: Request):
    with Session() as session:
        user = principal(request, session)
        rate_limit(f"profile:{user.id}", 30)
        saved = session.get(Profile, user.id)
        if saved is None:
            saved = Profile(account_id=user.id)
            session.add(saved)
        # Older clients send the original profile fields but omit resume highlights.
        highlights = ("education", "experience", "projects", "links")
        previous = saved.data or {}
        saved.data = body.model_dump()
        for field in highlights:
            if field not in body.model_fields_set and field in previous:
                saved.data[field] = previous[field]
        saved.updated_at = now()
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(
                409, "Account changed while saving profile; sign in again"
            ) from error
        return {**saved.data, "updated_at": saved.updated_at}


@router.delete("/me", status_code=204, dependencies=write_guard)
def delete_account(body: PasswordConfirmation, request: Request, response: Response):
    with Session() as session:
        user = principal(request, session)
        rate_limit(f"delete-account:{user.id}", 5)
        if not passwords.verify(body.password.get_secret_value(), user.password_hash):
            raise HTTPException(401, "Current password is incorrect")
        posting_sources = select(EmployerPosting.source_id).where(
            EmployerPosting.account_id == user.id
        )
        session.execute(
            update(Observation)
            .where(Observation.source_id.in_(posting_sources))
            .values(status="closed")
        )
        for model in (AccountSession, Profile, Resume, EmployerPosting, OAuthIdentity):
            session.execute(delete(model).where(model.account_id == user.id))
        session.delete(user)
        session.commit()
    clear_cookie(response)
