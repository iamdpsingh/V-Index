"""Expire authentication artifacts, without deleting user profiles or job evidence."""

import asyncio
from datetime import timedelta

from sqlalchemy import delete, update

from vindex.accounts.models import Account, AccountSession
from vindex.db import Run, Session, now


def expire_auth_artifacts(session, checked=None) -> None:
    checked = checked or now()
    session.execute(delete(AccountSession).where(AccountSession.expires_at <= checked))
    session.execute(
        update(Account)
        .where(Account.email_code_expires_at <= checked)
        .values(email_code_hash=None, email_code_expires_at=None)
    )
    session.execute(
        update(Account)
        .where(Account.password_reset_expires_at <= checked)
        .values(password_reset_hash=None, password_reset_expires_at=None)
    )


def retire_abandoned_runs(session, checked=None) -> None:
    checked = checked or now()
    # All refresh/lease budgets are <= 35 minutes. Never alter job observations.
    session.execute(
        update(Run)
        .where(Run.status == "running", Run.started_at < checked - timedelta(hours=1))
        .values(
            status="failed",
            finished_at=checked,
            error="Previous worker stopped before refresh completed",
        )
    )


async def maintain() -> None:
    from vindex.operations import log_event

    while True:
        try:
            with Session() as session:
                expire_auth_artifacts(session)
                retire_abandoned_runs(session)
                session.commit()
        except Exception as error:
            log_event("maintenance_failed", error_kind=type(error).__name__)
            await asyncio.sleep(300)
        else:
            await asyncio.sleep(3600)
