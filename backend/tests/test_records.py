from copy import deepcopy
from datetime import timedelta

import pytest
from sqlalchemy import select
from vindex.db import Job, Observation, Source, now
from vindex.ingest import aware, ingest
from vindex.records import public_job, public_record, salary
from vindex.schemas import Enumeration, JobInput, JobOut


@pytest.mark.parametrize(
    "source",
    [
        {"currency": "usd", "minimum": "900.00", "maximum": "1400.00", "schedule": "monthly"},
        {
            "@type": "MonetaryAmount",
            "currency": "USD",
            "value": {"minValue": 900, "maxValue": 1400, "unitText": "MONTH"},
        },
        {"currency": "USD", "min": 900, "max": 1400, "period": "month"},
        {
            "compensation_currency": "USD",
            "compensation_minimum": 900,
            "compensation_maximum": 1400,
            "compensation_frequency": "monthly",
        },
    ],
)
def test_salary_shapes_have_one_contract_without_altering_source(source):
    original = deepcopy(source)
    result, flags = salary(source)
    assert (result["min"], result["max"], result["currency"], result["period"]) == (
        900,
        1400,
        "USD",
        "month",
    )
    assert result["source"] == original and source == original and not flags
    assert salary(result)[0] == result


def test_salary_does_not_merge_currencies_or_treat_equity_as_wages():
    result, _ = salary(
        {
            "compensationTiers": [
                {
                    "title": "Europe",
                    "components": [
                        {
                            "compensationType": "Salary",
                            "minValue": 50000,
                            "maxValue": 60000,
                            "currencyCode": "EUR",
                            "interval": "1 YEAR",
                        },
                        {"compensationType": "EquityPercentage", "minValue": 1, "maxValue": 2},
                    ],
                },
                {
                    "title": "USA",
                    "components": [
                        {
                            "compensationType": "Salary",
                            "minValue": 70000,
                            "maxValue": 80000,
                            "currencyCode": "USD",
                            "interval": "1 YEAR",
                        }
                    ],
                },
            ]
        }
    )
    assert result["min"] is None and result["currency"] is None
    assert {r["currency"] for r in result["ranges"]} == {"EUR", "USD"}
    assert len(result["ranges"]) == 2
    text, _ = salary({"text": "$40–$50 depending on location"})
    assert text["min"] is None and text["currency"] is None
    assert text["text"] == "$40–$50 depending on location"
    bad, flags = salary({"min": 100, "max": 50})
    assert bad["min"] is None and "salary_range_invalid" in flags


def test_public_normalization_preserves_qualifiers_unknowns_and_source_observations():
    data = {
        "title": " Engineer ",
        "company": "Example",
        "description": "Full text. ",
        "location": "",
        "employment_type": '["PART_TIME","FULL_TIME"]',
        "remote_status": "Fully remote, within chosen locations",
        "salary": {"source_text": "Negotiable"},
        "published_at": "2026-11-19",
        "raw": {"private": "not public"},
    }
    before = deepcopy(data)
    record = public_record(data)
    assert record["employment_type"] == "Part-time; Full-time"
    assert record["employment_type_source"] == data["employment_type"]
    assert record["remote_status"] == data["remote_status"]
    assert record["description"] == "Full text. "
    assert "location_missing" in record["quality_flags"]
    assert "publication_timezone_unspecified" in record["quality_flags"]
    assert "raw" not in record and data == before
    assert public_record(record) == record


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/apply",
        "https://127.0.0.1/apply",
        "https://169.254.169.254/latest",
        "https://[::1]/apply",
        "https://example.org:8443/apply",
        "https://user:password@example.org/apply",
        "https://example.org/a b",
        "https://2130706433/apply",
        "https://0x7f000001/apply",
    ],
)
def test_job_input_rejects_nonpublic_or_malformed_application_links(url):
    with pytest.raises(ValueError):
        JobInput(
            external_id="1",
            title="Engineer",
            company="Example",
            description="Work",
            source_url="https://example.org/jobs/1",
            application_url=url,
        )


def test_whitespace_only_required_identity_is_invalid():
    with pytest.raises(ValueError):
        JobInput(
            external_id="1",
            title=" ",
            company="Example",
            description="",
            source_url="https://example.org/jobs/1",
            application_url="https://example.org/apply/1",
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_salary_rejects_nested_nonfinite_json_numbers(value):
    with pytest.raises(ValueError, match="finite JSON"):
        JobInput(
            external_id="1",
            title="Engineer",
            company="Example",
            description="Work",
            source_url="https://example.org/jobs/1",
            application_url="https://example.org/apply/1",
            salary={"ranges": [{"min": value}]},
        )


def test_schema_org_nested_single_salary_preserves_unspecified_period():
    result, flags = salary(
        {"currency": "GBP", "value": {"@type": "PropertyValue", "value": "55000"}}
    )
    assert result["min"] == result["max"] == 55000
    assert result["currency"] == "GBP" and result["period"] is None
    assert not flags


def test_unrecognized_salary_structure_stays_available_without_crashing_search():
    original = {"compensationTiers": [None, {"components": 5}], "ranges": 123}
    normalized, flags = salary(original)
    assert normalized["source"] == original and normalized["min"] is None
    assert "salary_structure_unmapped" in flags


def test_merged_timestamps_never_regress_and_title_changes_keep_first_seen(database, source):
    start = now() - timedelta(days=2)

    def posting(**overrides):
        return JobInput(
            **{
                "external_id": "1",
                "title": "Engineer",
                "company": "Example",
                "description": "Work",
                "location": "London",
                "source_url": "https://example.org/jobs/1",
                "application_url": "https://example.org/apply/1",
                **overrides,
            }
        )

    with database() as session:
        second = Source(
            provider="lever", slug="another", company="Example", url="https://jobs.lever.co/another"
        )
        session.add(second)
        session.flush()
        ingest(session, source, Enumeration(jobs=[posting()], complete=True), start)
        ingest(session, second, Enumeration(jobs=[posting()], complete=True), start)
        session.commit()
        changed = start + timedelta(hours=2)
        ingest(
            session,
            source,
            Enumeration(jobs=[posting(description="Changed")], complete=True),
            changed,
        )
        session.commit()
        ingest(
            session,
            second,
            Enumeration(jobs=[posting()], complete=True),
            changed + timedelta(hours=1),
        )
        session.commit()
        job = session.scalar(select(Job))
        assert aware(job.last_changed) == changed
        ingest(
            session,
            source,
            Enumeration(jobs=[posting(title="Senior Engineer")], complete=True),
            changed + timedelta(hours=2),
        )
        session.commit()
        observation = session.scalar(select(Observation).where(Observation.source_id == source.id))
        current = session.get(Job, observation.job_id)
        assert aware(current.first_seen) == start
        rows = list(session.scalars(select(Observation).where(Observation.job_id == current.id)))
        payload = public_job(current, rows)
        assert payload["first_seen_at"] == start
        assert payload["last_checked_at"] == changed + timedelta(hours=2)
        assert payload["sources"][0]["first_seen_at"] == start
        JobOut.model_validate(payload)
