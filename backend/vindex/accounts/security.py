import hashlib
import os
import secrets
from contextlib import contextmanager
from datetime import timedelta
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, Response
from pwdlib import PasswordHash
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from vindex.accounts.models import Account, AccountSession
from vindex.db import now
from vindex.ingest import aware

passwords = PasswordHash.recommended()
DUMMY_HASH = passwords.hash("A fixed timing equalization input, never an account credential")
SESSION_SECONDS = 7 * 24 * 3600
LIMIT_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[2]) end
if count > tonumber(ARGV[1]) then return 0 end
return 1
"""


def account_origin() -> str:
    raw = os.getenv("PUBLIC_WEB_ORIGIN", "").rstrip("/")
    try:
        parsed = urlsplit(raw)
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        valid = parsed.scheme == "https" or (parsed.scheme == "http" and local)
        if (
            not valid
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid account origin")
        _ = parsed.port
    except ValueError as error:
        raise HTTPException(503, "Account service is temporarily unavailable") from error
    return raw


def cookie_name() -> str:
    return (
        "__Host-vindex_session" if account_origin().startswith("https:") else "vindex_session_dev"
    )


def require_origin(request: Request) -> None:
    if request.headers.get("origin") != account_origin():
        raise HTTPException(403, "Request origin rejected")


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def redis_client() -> Redis:
    return Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def rate_limit(bucket: str, limit: int, window: int = 60) -> None:
    key = "vindex:account-rate:" + token_digest(bucket)
    try:
        allowed = redis_client().eval(LIMIT_SCRIPT, 1, key, str(limit), str(window))
    except RedisError as error:
        raise HTTPException(503, "Account service temporarily unavailable") from error
    if not allowed:
        raise HTTPException(429, "Too many requests", headers={"Retry-After": str(window)})


def credential_rate(request: Request, email: str, *, signup: bool = False) -> None:
    peer = request.client.host if request.client else "unknown"
    rate_limit(f"credentials:ip:{peer}", 20 if signup else 60, 3600 if signup else 60)
    rate_limit(f"credentials:email:{email}", 10)


def principal(request: Request, session: Session) -> Account:
    account_origin()
    token = request.cookies.get(cookie_name(), "")
    if not token or len(token) > 100:
        raise HTTPException(401, "Sign in required")
    entry = session.get(AccountSession, token_digest(token))
    if entry is None or aware(entry.expires_at) <= now():
        raise HTTPException(401, "Session expired or invalid")
    account = session.get(Account, entry.account_id)
    if account is None:
        raise HTTPException(401, "Session expired or invalid")
    return account


def issue_session(session: Session, account: Account, request: Request, response: Response) -> None:
    previous = request.cookies.get(cookie_name())
    if previous:
        session.execute(
            delete(AccountSession).where(AccountSession.token_hash == token_digest(previous))
        )
    session.execute(delete(AccountSession).where(AccountSession.expires_at <= now()))
    old = list(
        session.scalars(
            select(AccountSession)
            .where(AccountSession.account_id == account.id)
            .order_by(AccountSession.created_at.desc(), AccountSession.token_hash)
            .offset(9)
        )
    )
    for entry in old:
        session.delete(entry)
    token = secrets.token_urlsafe(32)
    session.add(
        AccountSession(
            token_hash=token_digest(token),
            account_id=account.id,
            expires_at=now() + timedelta(seconds=SESSION_SECONDS),
        )
    )
    response.set_cookie(
        cookie_name(),
        token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=account_origin().startswith("https:"),
        samesite="lax",
        path="/",
    )


def clear_cookie(response: Response) -> None:
    response.delete_cookie(
        cookie_name(),
        path="/",
        secure=account_origin().startswith("https:"),
        httponly=True,
        samesite="lax",
    )


@contextmanager
def parser_slot():
    """Two bounded parser processes at once across API replicas using this Redis."""
    client = redis_client()
    acquired = None
    try:
        for index in range(2):
            lock = client.lock(f"vindex:resume-parser:{index}", timeout=30)
            if lock.acquire(blocking=False):
                acquired = lock
                break
        if acquired is None:
            raise HTTPException(
                429, "Resume processing busy; retry shortly", headers={"Retry-After": "2"}
            )
        yield
    except RedisError as error:
        raise HTTPException(503, "Resume processing temporarily unavailable") from error
    finally:
        if acquired is not None:
            try:
                acquired.release()
            except RedisError:
                pass  # Lease expiry bounds recovery; no private content enters logs.
