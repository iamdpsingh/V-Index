from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from vindex import api

from scripts.check_production import alert_message, evaluate, main


def healthy():
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "redis_available": True,
        "live_workers": 1,
        "counts": {"failing": 2, "stale": 0, "abandoned_runs": 0},
        "backup": {"status": "success", "at": datetime.now(UTC).isoformat()},
    }


@pytest.mark.parametrize("condition", ["worker", "backup", "stale", "old_report"])
def test_external_probe_detects_distinct_outages_without_equating_source_failure_to_closure(
    condition,
):
    report = healthy()
    assert evaluate(report, datetime.now(UTC)) == []
    if condition == "worker":
        report["live_workers"] = 0
    elif condition == "backup":
        report["backup"]["at"] = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    elif condition == "stale":
        report["counts"]["stale"] = 1
    else:
        report["checked_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    assert evaluate(report, datetime.now(UTC))


def test_monitoring_token_is_scoped_and_aggregate_only(monkeypatch):
    monkeypatch.setenv("MONITOR_TOKEN", "monitor-test-" + "x" * 32)
    monkeypatch.setenv("ADMIN_TOKEN", "separate-operator-" + "y" * 32)
    monkeypatch.setattr(api, "rate_limit", lambda *args: None)
    monkeypatch.setattr(api, "Session", lambda: Mock(__enter__=Mock(), __exit__=Mock()))
    report = {
        **healthy(),
        "workers": {"live": 1},
        "alerts": [],
        "sources": [
            {
                "source_id": 15,
                "provider": "jobboardfire",
                "stale": True,
                "initial_index_complete": True,
                "consecutive_failures": 1,
                "failure_kind": "HTTPStatusError",
                "failure_category": "access_denied",
                "source_url": "https://PRIVATE_CANARY/",
                "raw_error": "PRIVATE_CANARY",
            }
        ],
    }
    monkeypatch.setattr(api, "snapshot", lambda session: report)
    client = TestClient(api.app)
    assert client.get("/api/v1/monitoring").status_code == 401
    headers = {"Authorization": "Bearer monitor-test-" + "x" * 32}
    response = client.get("/api/v1/monitoring", headers=headers)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert "PRIVATE_CANARY" not in response.text and "sources" not in response.json()
    issue = response.json()["source_issues"][0]
    assert issue["source_id"] == 15 and issue["failure_category"] == "access_denied"
    assert "source_url" not in issue and "raw_error" not in issue
    assert client.get("/api/v1/sources", headers=headers).status_code == 401


def test_stale_sources_still_fail_with_actionable_safe_annotations(monkeypatch, capsys):
    report = {
        **healthy(),
        "critical_alerts": ["stale_sources_or_abandoned_runs"],
        "source_issues": [
            {"source_id": 15, "provider": "jobboardfire", "stale": True},
            {"source_id": 42, "provider": "jobkit", "stale": True},
            {"source_id": 43, "provider": "\n::error::PRIVATE_CANARY", "stale": True},
        ],
    }
    report["counts"]["stale"] = 3
    monkeypatch.setattr("scripts.check_production.run", lambda: report)
    with pytest.raises(SystemExit) as stopped:
        main()
    assert stopped.value.code == 1
    annotations = [
        line for line in capsys.readouterr().out.splitlines() if line.startswith("::error")
    ]
    assert len(annotations) == 1
    assert "3 stale sources" in annotations[0]
    assert "jobboardfire #15, jobkit #42" in annotations[0]
    assert "PRIVATE_CANARY" not in annotations[0]
    assert "do not bypass access controls" in annotations[0]


def test_alert_drill_annotation_does_not_claim_a_real_outage():
    assert "not a real outage" in alert_message("controlled_alert_drill_not_a_real_outage", {})
