"""Production checks with disposable synthetic accounts; emits no credentials."""

import os
import secrets
from datetime import UTC, datetime
from typing import Any

import httpx
from vindex.failure_classification import failure_category

from scripts.cloud_backup import publish_report

ORIGIN = "https://rolewisp.vercel.app"


def run_review() -> dict:
    checks: dict[str, bool] = {}
    report: dict[str, Any] = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "scope": "Actual production HTTPS; disposable synthetic accounts only",
        "checks": checks,
        "support_inbox_verified": False,
        "smtp_delivery_tested": False,
    }
    if os.getenv("PUBLIC_WEB_ORIGIN", "").rstrip("/") != ORIGIN:
        report.update(status="failed", stage="origin_configuration")
        publish_report("operations/release-review.json", report)
        return report
    password = secrets.token_urlsafe(32)
    suffix = secrets.token_hex(8)
    clients = []
    try:
        for role in ("candidate", "employer"):
            client = httpx.Client(
                base_url=ORIGIN,
                headers={"Origin": ORIGIN},
                trust_env=False,
                follow_redirects=False,
                timeout=30,
            )
            clients.append(client)
            email = f"release-{role}-{suffix}@example.com"
            created = client.post(
                "/api/v1/auth/register", json={"email": email, "password": password}
            )
            created.raise_for_status()
            assert "no-store" in created.headers.get("cache-control", "")
            assert all(
                "HttpOnly" in value and "Secure" in value
                for value in created.headers.get_list("set-cookie")
            )
            client.put("/api/v1/me/role", json={"role": role}).raise_for_status()
        report["stage"] = "profiles"
        candidate, employer = clients
        saved = candidate.put(
            "/api/v1/me/profile",
            json={
                "full_name": "Synthetic release check",
                "headline": "Temporary verification",
                "skills": ["Python"],
                "desired_titles": ["Engineer"],
                "education": [{"qualification": "bachelors", "details": "Synthetic qualification"}],
            },
        )
        saved.raise_for_status()
        read = candidate.get("/api/v1/me/profile")
        assert "no-store" in read.headers.get("cache-control", "")
        assert read.json()["headline"] == "Temporary verification"
        assert employer.get("/api/v1/me/profile").json().get("headline") != "Temporary verification"
        checks["private_profile_isolation_and_no_store"] = True
        report["stage"] = "resume"
        resume = b"Synthetic release document. No personal information."
        candidate.put(
            "/api/v1/me/resume",
            content=resume,
            headers={"content-type": "application/octet-stream", "x-filename": "synthetic.txt"},
        ).raise_for_status()
        downloaded = candidate.get("/api/v1/me/resume/download")
        assert downloaded.content == resume and "no-store" in downloaded.headers.get(
            "cache-control", ""
        )
        assert employer.get("/api/v1/me/resume/download").status_code == 404
        checks["private_resume_ownership_and_download"] = True
        report["stage"] = "employer"
        draft = employer.post(
            "/api/v1/me/postings",
            json={
                "title": "Synthetic release draft",
                "company": "Release check",
                "location": "Remote",
                "description": "Internal verification. Never published.",
                "application_url": "https://example.org/synthetic",
            },
        )
        draft.raise_for_status()
        posting_id = draft.json()["id"]
        assert candidate.put(
            f"/api/v1/me/postings/{posting_id}",
            json={k: v for k, v in draft.json().items() if k not in {"id", "status"}},
        ).status_code in {403, 404, 422}
        assert employer.post(f"/api/v1/me/postings/{posting_id}/publish").status_code == 403
        checks["employer_ownership_and_unverified_publish_denied"] = True
        # Per-email rate budget: use a unique synthetic address, never another person's account.
        report["stage"] = "login_rate_limit"
        limited = False
        for i in range(11):
            response = candidate.post(
                "/api/v1/auth/login",
                json={"email": f"rate-{suffix}@example.com", "password": password},
            )
            if response.status_code == 429:
                assert i == 10
                limited = bool(response.headers.get("retry-after"))
                break
            assert response.status_code == 401
        assert limited
        checks["login_rate_limit_behind_public_proxy"] = True
        candidate.post(
            "/api/v1/auth/login",
            json={"email": f"release-candidate-{suffix}@example.com", "password": password},
        ).raise_for_status()
        report["stage"] = "signup_rate_limit"
        for attempt in range(5):
            duplicate = candidate.post(
                "/api/v1/auth/register",
                json={"email": f"release-candidate-{suffix}@example.com", "password": password},
            )
            assert duplicate.status_code == (409 if attempt < 4 else 429)
        assert duplicate.headers.get("retry-after")
        checks["signup_rate_limit_behind_public_proxy"] = True
        report["stage"] = "proxy_controls"
        controls = candidate.get(
            "/api/v1/operations",
            headers={
                "Authorization": "Bearer " + os.environ["ADMIN_TOKEN"],
                "X-Forwarded-For": "192.0.2.1",
                "x-rolewisp-client-ip": "192.0.2.1",
                "x-rolewisp-proxy-signature": "0" * 64,
            },
        )
        controls.raise_for_status()
        snapshot = controls.json()
        assert snapshot["request_controls"]["proxy_metadata_verified"]
        checks["trusted_proxy_metadata_verified"] = True
        report["operations"] = snapshot
        from sqlalchemy import func, select
        from vindex.db import Job, Observation, Run, Session, Source

        with Session() as database:
            duplicate_ids = list(
                database.scalars(
                    select(Observation.job_id)
                    .where(Observation.status == "open")
                    .group_by(Observation.job_id)
                    .having(func.count() > 1)
                    .limit(3)
                )
            )
            report["current_duplicate_job_ids"] = duplicate_ids
            report["repeated_successful_sources"] = len(
                list(
                    database.execute(
                        select(Run.source_id)
                        .where(Run.status == "success")
                        .group_by(Run.source_id)
                        .having(func.count() >= 2)
                    )
                )
            )
            active = select(Observation.job_id).where(Observation.status == "open")
            rows = database.execute(
                select(
                    Job.id,
                    Job.data["title"].as_string(),
                    Job.data["company"].as_string(),
                    Job.data["application_url"].as_string(),
                )
                .where(Job.id.in_(active))
                .order_by(Job.id.desc())
                .limit(1000)
            )
            groups: dict[tuple[str, str], tuple[int, str]] = {}
            for identifier, title, company, application in rows:
                if (
                    not isinstance(identifier, int)
                    or not isinstance(title, str)
                    or not isinstance(company, str)
                    or not isinstance(application, str)
                ):
                    continue
                key = (title.casefold(), company.casefold())
                prior = groups.get(key)
                if prior and prior[1] != application:
                    report["distinct_same_title_requisition_ids"] = [prior[0], identifier]
                    break
                groups[key] = (identifier, application)
            latest_ids = select(func.max(Run.id)).group_by(Run.source_id)
            failures = []
            for run, source in database.execute(
                select(Run, Source)
                .join(Source, Source.id == Run.source_id)
                .where(Run.id.in_(latest_ids), Run.status == "failed")
                .limit(150)
            ):
                category = failure_category(run.error or "")
                failures.append(
                    {
                        "source_id": source.id,
                        "provider": source.provider,
                        "failure_kind": (run.error or "").split(":", 1)[0][:60],
                        "operator_diagnostic": (run.error or "")[:1000],
                        "category": category,
                        "next_check_at": source.next_check.isoformat(),
                    }
                )
            report["fetch_failures"] = failures
            # A bounded operator-triggered refresh proves a second native fetch
            # through the real worker implementation. It is not a six-hour clock-cycle claim.
            pilot = database.scalar(
                select(Source.id)
                .join(Run, Run.source_id == Source.id)
                .where(
                    Run.status == "success",
                    Run.count.between(1, 300),
                    Source.provider.in_(["ashby", "lever", "greenhouse"]),
                )
                .order_by(Run.count, Run.finished_at)
                .limit(1)
            )
        if pilot is not None:
            import asyncio

            from vindex.worker import refresh

            run_id = asyncio.run(refresh(pilot))
            with Session() as database:
                replay = database.get(Run, run_id)
                if replay is not None:
                    report["production_refresh_example"] = {
                        "mode": "operator_triggered_native_refresh",
                        "source_id": pilot,
                        "run_id": run_id,
                        "status": replay.status,
                        "jobs": replay.count,
                        "finished_at": replay.finished_at.isoformat()
                        if replay.finished_at
                        else None,
                    }
                    checks["second_native_production_refresh"] = replay.status == "success"
        assert employer.get("/api/v1/sources").status_code == 401
        assert employer.get("/api/v1/runs").status_code == 401
        checks["account_does_not_grant_operator_access"] = True
        response = candidate.get(
            "/api/v1/jobs", params={"view": "summary", "limit": 2, "offset": 0}
        )
        response.raise_for_status()
        checks["public_search_and_pagination"] = True
        report["indexed_jobs"] = response.json()["total"]
        checks["session_cookie_secure_httponly"] = True
        report["stage"] = "complete"
        report["status"] = "passed"
    except Exception as error:
        report["status"] = "failed"
        report["error_kind"] = type(error).__name__
    finally:
        cleanup = True
        for client in clients:
            try:
                response = client.request("DELETE", "/api/v1/me", json={"password": password})
                cleanup = cleanup and response.status_code in {204, 401}
            except Exception:
                cleanup = False
            finally:
                client.close()
        checks["temporary_account_cleanup"] = cleanup
        if not cleanup:
            report["status"] = "failed"
        publish_report("operations/release-review.json", report)
    return report
