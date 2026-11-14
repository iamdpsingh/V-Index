"""Issue and verify short-lived email codes for signed-in accounts."""

import hmac
import os
import secrets
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import delete, select
from sqlalchemy.orm import Session as DatabaseSession

from vindex.accounts.models import Account, AccountSession
from vindex.accounts.schemas import EmailCode, Registration
from vindex.accounts.security import (
    credential_rate,
    passwords,
    principal,
    rate_limit,
    require_origin,
    token_digest,
)
from vindex.db import Session, now
from vindex.ingest import aware

router = APIRouter(prefix="/api/v1/me", tags=["Private accounts"])
guard = [Depends(require_origin)]


def deliver(address: str, code: str, purpose: str = "Verify your Rolewisp email") -> None:
    host, sender = os.getenv("SMTP_HOST"), os.getenv("SMTP_FROM")
    if not host or not sender:
        raise HTTPException(503, "Email delivery is unavailable")
    message = EmailMessage()
    message["From"], message["To"] = sender, address
    message["Subject"] = purpose
    message.set_content(f"Your Rolewisp code is {code}. It expires in 15 minutes.")
    try:
        with smtplib.SMTP_SSL(
            host,
            int(os.getenv("SMTP_PORT") or "465"),
            timeout=8,
            context=ssl.create_default_context(),
        ) as connection:
            if username := os.getenv("SMTP_USERNAME"):
                connection.login(username, os.environ["SMTP_PASSWORD"])
            if connection.send_message(message):
                raise smtplib.SMTPException("Recipient rejected")
    except (OSError, ValueError, KeyError) as error:
        raise HTTPException(503, "Email delivery is unavailable") from error


def locked_account(request: Request, session: DatabaseSession) -> Account:
    account = principal(request, session)
    result = session.scalar(select(Account).where(Account.id == account.id).with_for_update())
    if result is None:
        raise HTTPException(401, "Account is unavailable")
    return result


@router.post("/email/verification", status_code=204, dependencies=guard)
def send_verification(request: Request) -> None:
    with Session() as session:
        account = locked_account(request, session)
        if account.email_verified_at:
            return
        rate_limit(f"email-code-send:{account.id}", 3, 900)
        code = f"{secrets.randbelow(10**8):08d}"
        account.email_code_hash = token_digest(account.id + ":" + code)
        account.email_code_expires_at = now() + timedelta(minutes=15)
        deliver(account.email, code)
        session.commit()


@router.post("/email/verification/confirm", status_code=204, dependencies=guard)
def confirm_verification(body: EmailCode, request: Request) -> None:
    with Session() as session:
        account = locked_account(request, session)
        rate_limit(f"email-code-confirm:{account.id}", 8, 900)
        if (
            not account.email_code_hash
            or not account.email_code_expires_at
            or aware(account.email_code_expires_at) <= now()
            or not hmac.compare_digest(
                account.email_code_hash, token_digest(account.id + ":" + body.code)
            )
        ):
            raise HTTPException(422, "Invalid or expired verification code")
        account.email_verified_at = now()
        account.email_code_hash = None
        account.email_code_expires_at = None
        session.commit()


recovery_router = APIRouter(prefix="/api/v1/auth/password-reset", tags=["Private accounts"])


class ResetRequest(BaseModel):
    email: EmailStr


class ResetConfirmation(Registration, EmailCode):
    pass


@recovery_router.post("", status_code=204, dependencies=guard)
def send_reset(body: ResetRequest, request: Request) -> None:
    email = str(body.email).casefold()
    credential_rate(request, email)
    if not os.getenv("SMTP_HOST") or not os.getenv("SMTP_FROM"):
        raise HTTPException(503, "Email delivery is unavailable")
    with Session() as session:
        account = session.scalar(select(Account).where(Account.email == email).with_for_update())
        if not account or not account.email_verified_at:
            return
        code = f"{secrets.randbelow(10**8):08d}"
        account.password_reset_hash = token_digest(account.id + ":reset:" + code)
        account.password_reset_expires_at = now() + timedelta(minutes=15)
        try:
            deliver(account.email, code, "Reset your Rolewisp password")
        except HTTPException:
            return
        session.commit()


@recovery_router.post("/confirm", status_code=204, dependencies=guard)
def confirm_reset(body: ResetConfirmation, request: Request) -> None:
    email = str(body.email).casefold()
    credential_rate(request, email)
    with Session() as session:
        account = session.scalar(select(Account).where(Account.email == email).with_for_update())
        if (
            not account
            or not account.password_reset_hash
            or not account.password_reset_expires_at
            or aware(account.password_reset_expires_at) <= now()
            or not hmac.compare_digest(
                account.password_reset_hash, token_digest(account.id + ":reset:" + body.code)
            )
        ):
            raise HTTPException(422, "Invalid or expired reset code")
        account.password_hash = passwords.hash(body.password.get_secret_value())
        account.password_reset_hash = None
        account.password_reset_expires_at = None
        session.execute(delete(AccountSession).where(AccountSession.account_id == account.id))
        session.commit()
