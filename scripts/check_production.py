"""Independent, read-only production probe; no third-party telemetry or private records."""

import json
import os
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

ORIGIN = "https://rolewisp.vercel.app"
MAX_BODY = 200_000


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Production probe refused a redirect")


def evaluate(report: dict, checked: datetime) -> list[str]:
    alerts = []
    if not report.get("redis_available") or report.get("live_workers", 0) < 1:
        alerts.append("worker_or_redis_unavailable")
    stamp = datetime.fromisoformat(report["checked_at"].replace("Z", "+00:00"))
    if stamp.tzinfo is None or not checked - timedelta(minutes=5) < stamp < checked + timedelta(
        minutes=5
    ):
        alerts.append("stale_monitoring_response")
    backup = report.get("backup", {})
    if backup.get("status") != "success" or not backup.get("at"):
        alerts.append("backup_not_successful")
    else:
        at = datetime.fromisoformat(backup["at"].replace("Z", "+00:00"))
        if at.tzinfo is None or not checked - timedelta(hours=36) < at < checked + timedelta(
            minutes=5
        ):
            alerts.append("backup_overdue")
    if report["counts"].get("stale", 0) or report["counts"].get("abandoned_runs", 0):
        alerts.append("stale_sources_or_abandoned_runs")
    return alerts


def run() -> dict:
    token = os.environ.get("MONITOR_TOKEN", "")
    if len(token) < 32:
        raise ValueError("Configure the dedicated monitoring secret")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoRedirect(),
    )

    def read(path: str, private: bool = False) -> dict:
        request = urllib.request.Request(
            ORIGIN + path,
            headers={"Authorization": "Bearer " + token} if private else {},
        )
        with opener.open(request, timeout=20) as response:
            if "no-store" not in response.headers.get("cache-control", ""):
                raise ValueError("Production API response was cacheable")
            body = response.read(MAX_BODY + 1)
        if len(body) > MAX_BODY:
            raise ValueError("Production probe response exceeded its bound")
        return json.loads(body)

    jobs = read("/api/v1/jobs?view=summary&limit=1")
    if not isinstance(jobs.get("total"), int) or jobs["total"] <= 0 or not jobs.get("items"):
        raise ValueError("Production search has no usable indexed jobs")
    report = read("/api/v1/monitoring", private=True)
    checked = datetime.now(UTC)
    alerts = evaluate(report, checked)
    drill = os.getenv("MONITOR_ALERT_DRILL", "false").lower() == "true"
    if drill:
        alerts.append("controlled_alert_drill_not_a_real_outage")
    return {
        "checked_at": checked.isoformat(),
        "scope": "Independent HTTPS probe; aggregate metadata only",
        "indexed_jobs": jobs["total"],
        "live_workers": report["live_workers"],
        "counts": report["counts"],
        "source_issues": report.get("source_issues", []),
        "issues_truncated": report.get("issues_truncated", False),
        "backup": report["backup"],
        "critical_alerts": alerts,
        "controlled_drill": drill,
    }


def main() -> None:
    try:
        report = run()
    except Exception as error:
        # HTTP errors/URLs and body data must not expose credentials in Actions logs.
        print(json.dumps({"status": "failed", "error_kind": type(error).__name__}))
        print("::error title=Rolewisp production monitor::Production probe failed")
        raise SystemExit(1) from None
    print(json.dumps(report, sort_keys=True))
    if report["counts"].get("failing", 0):
        print(
            "::warning title=Rolewisp source health::Some sources are failing; inspect operator diagnostics"
        )
    if report["critical_alerts"]:
        print(
            "::error title=Rolewisp production monitor::Critical condition or explicitly labelled alert drill"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
