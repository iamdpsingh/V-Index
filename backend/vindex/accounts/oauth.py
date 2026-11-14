"""Optional social sign-in backed by fixed provider endpoints and one-time state."""

import hashlib
import os
import secrets
from base64 import urlsafe_b64encode
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import EmailStr, TypeAdapter, ValidationError
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError

from vindex.accounts.models import Account, OAuthIdentity, Profile
from vindex.accounts.schemas import ProfileInput
from vindex.accounts.security import (
    account_origin,
    issue_session,
    passwords,
    rate_limit,
    redis_client,
)
from vindex.db import Session, now

router = APIRouter(prefix="/api/v1/auth/oauth")
PROVIDERS = {
    "google": (
        "https://accounts.google.com/o/oauth2/v2/auth",
        "https://oauth2.googleapis.com/token",
        "https://openidconnect.googleapis.com/v1/userinfo",
        "openid email",
        True,
    ),
    "linkedin": (
        "https://www.linkedin.com/oauth/v2/authorization",
        "https://www.linkedin.com/oauth/v2/accessToken",
        "https://api.linkedin.com/v2/userinfo",
        "openid profile email",
        False,
    ),
    "github": (
        "https://github.com/login/oauth/authorize",
        "https://github.com/login/oauth/access_token",
        "https://api.github.com/user/emails",
        "user:email",
        True,
    ),
}
email_type = TypeAdapter(EmailStr)


def credentials(provider: str) -> tuple[str, str]:
    return tuple_credentials(provider.upper())


def tuple_credentials(prefix: str) -> tuple[str, str]:
    return os.getenv(f"OAUTH_{prefix}_CLIENT_ID", ""), os.getenv(
        f"OAUTH_{prefix}_CLIENT_SECRET", ""
    )


@router.get("")
def enabled_providers() -> list[str]:
    return [provider for provider in PROVIDERS if all(credentials(provider))]


def configured(provider: str) -> tuple[str, str]:
    if provider not in enabled_providers():
        raise HTTPException(404, "Social sign-in provider unavailable")
    return credentials(provider)


def callback_url(provider: str) -> str:
    return f"{account_origin()}/api/v1/auth/oauth/{provider}/callback"


@router.get("/{provider}/start")
def start(provider: str, request: Request):
    client_id, _ = configured(provider)
    rate_limit(f"oauth:{request.client.host if request.client else 'unknown'}", 20)
    authorize, _, _, scope, pkce = PROVIDERS[provider]
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    try:
        redis_client().setex(f"vindex:oauth:{provider}:{state}", 600, verifier)
    except RedisError as error:
        raise HTTPException(503, "Social sign-in temporarily unavailable") from error
    query = dict(
        client_id=client_id,
        redirect_uri=callback_url(provider),
        response_type="code",
        scope=scope,
        state=state,
    )
    if pkce:
        query["code_challenge"] = (
            urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
        )
        query["code_challenge_method"] = "S256"
    response = RedirectResponse(authorize + "?" + urlencode(query))
    response.set_cookie(
        "rolewisp_oauth",
        state,
        max_age=600,
        httponly=True,
        samesite="lax",
        secure=account_origin().startswith("https:"),
        path="/api/v1/auth/oauth",
    )
    return response


@router.get("/{provider}/callback")
def callback(provider: str, request: Request, state: str = "", code: str = ""):
    client_id, secret = configured(provider)
    _, exchange, userinfo, _, pkce = PROVIDERS[provider]
    response = RedirectResponse(account_origin() + "/?tab=profile", status_code=303)
    response.delete_cookie("rolewisp_oauth", path="/api/v1/auth/oauth")
    try:
        cookie = request.cookies.get("rolewisp_oauth", "")
        if not state or len(state) > 100 or not secrets.compare_digest(state, cookie) or not code:
            raise ValueError("Invalid challenge")
        verifier = redis_client().getdel(f"vindex:oauth:{provider}:{state}")
        if not isinstance(verifier, bytes):
            raise ValueError("Expired challenge")
        payload = dict(
            code=code,
            client_id=client_id,
            client_secret=secret,
            redirect_uri=callback_url(provider),
            grant_type="authorization_code",
        )
        if pkce:
            payload["code_verifier"] = verifier.decode()
        with httpx.Client(timeout=8, trust_env=False, follow_redirects=False) as client:
            token = client.post(exchange, data=payload, headers={"Accept": "application/json"})
            token.raise_for_status()
            headers = {
                "Authorization": "Bearer " + token.json()["access_token"],
                "Accept": "application/json",
            }
            profile = client.get(userinfo, headers=headers)
            profile.raise_for_status()
            identity = profile.json()
            if provider == "github":
                github_user = client.get("https://api.github.com/user", headers=headers)
                github_user.raise_for_status()
                github_id = github_user.json()["id"]
                if type(github_id) is not int or github_id < 1:
                    raise ValueError("Invalid GitHub account ID")
                subject = str(github_id)
            else:
                subject = identity["sub"]
        if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
            raise ValueError("Invalid provider account ID")
        if provider == "github":
            identity = next(
                (
                    row
                    for row in identity
                    if row.get("primary") is True and row.get("verified") is True
                ),
                {},
            )
            verified = "verified" in identity
        else:
            verified = identity.get("email_verified")
        if verified is not True:
            raise ValueError("Verified email missing")
        email = email_type.validate_python(identity["email"]).casefold()
        with Session() as session:
            link = session.get(OAuthIdentity, (provider, subject))
            account = session.get(Account, link.account_id) if link else None
            if account is None:
                if os.getenv("ACCOUNT_REGISTRATION_ENABLED", "false").lower() != "true":
                    raise ValueError("Registration unavailable")
                account = Account(
                    email=email,
                    email_verified_at=now(),
                    password_hash=passwords.hash(secrets.token_urlsafe(48)),
                )
                session.add(account)
                session.flush()
                session.add(Profile(account_id=account.id, data=ProfileInput().model_dump()))
                session.add(
                    OAuthIdentity(provider=provider, subject=subject, account_id=account.id)
                )
            issue_session(session, account, request, response)
            session.commit()
    except (
        httpx.HTTPError,
        RedisError,
        IntegrityError,
        ValidationError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
    ):
        failure = RedirectResponse(account_origin() + "/?auth_error=social", status_code=303)
        failure.delete_cookie("rolewisp_oauth", path="/api/v1/auth/oauth")
        return failure
    return response
