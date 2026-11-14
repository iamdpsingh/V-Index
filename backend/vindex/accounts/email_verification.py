"""Issue and verify short-lived email codes for signed-in accounts."""

import hmac
import os
import secrets
import smtplib
from datetime import timedelta
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DatabaseSession

from vindex.accounts.models import Account
from vindex.accounts.schemas import EmailCode
from vindex.accounts.security import principal, rate_limit, require_origin, token_digest
from vindex.db import Session, now
from vindex.ingest import aware

router = APIRouter(prefix="/api/v1/me", tags=["Private accounts"])
guard = [Depends(require_origin)]


def deliver(address: str, code: str) -> None:
    host, sender = os.getenv("SMTP_HOST"), os.getenv("SMTP_FROM")
    if not host or not sender:
        raise HTTPException(503, "Email delivery is unavailable")
    message = EmailMessage()
    message["From"], message["To"] = sender, address
    message["Subject"] = "Verify your Rolewisp email"
    message.set_content(f"Your Rolewisp verification code is {code}. It expires in 15 minutes.")
    try:
        with smtplib.SMTP_SSL(host, int(os.getenv("SMTP_PORT") or "465"), timeout=8) as connection:
            if username := os.getenv("SMTP_USERNAME"):
                connection.login(username, os.environ["SMTP_PASSWORD"])
            connection.send_message(message)
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
