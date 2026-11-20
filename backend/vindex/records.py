"""Consistent public records; immutable source observations remain unchanged."""

import json
import math
import re
from datetime import UTC, datetime
from typing import Any

from vindex.connectors.public import text
from vindex.db import Job, Observation


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


EMPLOYMENT = {
    "fulltime": "Full-time",
    "parttime": "Part-time",
    "contractor": "Contract",
    "contract": "Contract",
    "temporary": "Temporary",
    "temp": "Temporary",
    "intern": "Internship",
    "internship": "Internship",
    "volunteer": "Volunteer",
    "permanent": "Permanent",
    "freelance": "Freelance",
    "seasonal": "Seasonal",
    "apprentice": "Apprenticeship",
    "apprenticeship": "Apprenticeship",
    "casual": "Casual",
    "other": "Other",
}
WORKPLACE = {
    "remote": "Remote",
    "fullyremote": "Remote",
    "telecommute": "Remote",
    "telecommuting": "Remote",
    "hybrid": "Hybrid",
    "onsite": "On-site",
    "inoffice": "On-site",
    "office": "On-site",
    "remoteoption": "Remote option",
}
PERIODS = {
    **dict.fromkeys(("year", "yearly", "annual", "annually", "annum", "perannum", "1year"), "year"),
    **dict.fromkeys(("month", "monthly", "1month"), "month"),
    **dict.fromkeys(("week", "weekly", "1week"), "week"),
    **dict.fromkeys(("day", "daily", "1day"), "day"),
    **dict.fromkeys(("hour", "hourly", "hr", "1hour"), "hour"),
    **dict.fromkeys(("quarter", "quarterly"), "quarter"),
}


def employment(value: str | None) -> tuple[str | None, bool]:
    if not value or not value.strip():
        return None, False
    original = value.strip()
    parts = [original]
    if original.startswith("["):
        try:
            parsed = json.loads(original)
        except ValueError:
            parsed = None
        if isinstance(parsed, list) and all(isinstance(v, str) for v in parsed):
            parts = parsed
    elif any(mark in original for mark in (";", " / ")):
        parts = re.split(r";| / ", original)
    result = []
    unmapped = False
    for part in parts:
        if not part.strip():
            continue
        normalized = EMPLOYMENT.get(key(part))
        if normalized is None:
            normalized = part.strip()
            unmapped = True
        if normalized not in result:
            result.append(normalized)
    return "; ".join(result) or None, unmapped


def number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        # Parse explicit numeric fields only, never salary prose or currency symbols.
        value = value.strip()
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
            return None
    try:
        amount = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if not math.isfinite(amount) or amount < 0:
        return None
    return int(amount) if amount.is_integer() else amount


def first(row: dict, names: tuple[str, ...]) -> Any:
    return next((row[k] for k in names if row.get(k) not in (None, "")), None)


def salary_range(row: dict, label: str | None = None) -> dict[str, Any]:
    nested = row.get("value")
    value = nested if isinstance(nested, dict) else row
    minimum = first(
        value,
        (
            "min",
            "minimum",
            "minValue",
            "min_salary",
            "salary_min",
            "compensation_minimum",
            "minCompensation",
            "HiringMinRate",
        ),
    )
    maximum = first(
        value,
        (
            "max",
            "maximum",
            "maxValue",
            "max_salary",
            "salary_max",
            "compensation_maximum",
            "maxCompensation",
            "HiringMaxRate",
        ),
    )
    if minimum is None and maximum is None:
        single = first(value, ("amount", "HiringRate", "value"))
        if single is None and not isinstance(nested, dict):
            single = nested
        minimum = maximum = single
    currency = first(
        row,
        ("currency", "currencyCode", "currency_code", "salaryCurrency", "compensation_currency"),
    )
    currency = currency.upper().strip() if isinstance(currency, str) else None
    if currency is not None and not re.fullmatch(r"[A-Z]{3}", currency):
        currency = None
    unit = first(
        value,
        (
            "period",
            "unit",
            "unitText",
            "interval",
            "schedule",
            "pay_frequency",
            "compensation_frequency",
            "pay_type",
            "PayType",
        ),
    )
    if unit is None and value is not row:
        unit = first(row, ("period", "unit", "interval", "schedule", "pay_type"))
    return {
        "min": number(minimum),
        "max": number(maximum),
        "currency": currency,
        "period": PERIODS.get(key(unit)) if isinstance(unit, str) else None,
        "label": label if isinstance(label, str) else None,
    }


def salary(source: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[str]]:
    if not source:
        return None, []
    canonical_keys = {"min", "max", "currency", "period", "text", "ranges", "source"}
    if set(source) == canonical_keys:
        return source, []
    flags = []
    structured = source.get("structured")
    base = salary_range(structured if isinstance(structured, dict) else source)
    if base["currency"] is None:
        base["currency"] = salary_range(source)["currency"]
    base.pop("label")
    source_text = first(
        source,
        (
            "text",
            "source_text",
            "display_text",
            "compensation",
            "compensationTierSummary",
            "scrapeableCompensationSalarySummary",
        ),
    )
    if source_text is None and isinstance(source.get("value"), dict):
        value = source["value"].get("value")
        if isinstance(value, str) and number(value) is None:
            source_text = value
    if (
        source_text is None
        and isinstance(source.get("value"), str)
        and number(source["value"]) is None
    ):
        source_text = source["value"]
    label = text(source_text) if isinstance(source_text, str) else None
    ranges = []
    tiers = source.get("compensationTiers")
    for tier in tiers if isinstance(tiers, list) else []:
        if not isinstance(tier, dict):
            continue
        components = tier.get("components")
        for component in components if isinstance(components, list) else []:
            if isinstance(component, dict) and component.get("compensationType") == "Salary":
                ranges.append(salary_range(component, tier.get("title")))
    source_ranges = source.get("ranges")
    for row in source_ranges if isinstance(source_ranges, list) else []:
        if isinstance(row, dict):
            ranges.append(salary_range(row, row.get("location") or row.get("label")))
    if not ranges and isinstance(source.get("source_compensation"), dict):
        ranges.append(salary_range(source["source_compensation"]))
    ranges = list({json.dumps(row, sort_keys=True): row for row in ranges}.values())
    amounts = {
        (r["min"], r["max"], r["currency"], r["period"])
        for r in ranges
        if r["min"] is not None or r["max"] is not None
    }
    if len(amounts) == 1 and base["min"] is None and base["max"] is None:
        minimum, maximum, currency, period = next(iter(amounts))
        base.update(min=minimum, max=maximum, currency=currency, period=period)
    for row in [base, *ranges]:
        if row["min"] is not None and row["max"] is not None and row["min"] > row["max"]:
            row["min"] = row["max"] = None
            flags.append("salary_range_invalid")
    if base["min"] is None and base["max"] is None and not ranges and not label:
        flags.append("salary_structure_unmapped")
    # Keep the original public compensation object. Never combine currencies,
    # annualize hours, or infer a currency from the company's country.
    return {**base, "text": label or None, "ranges": ranges, "source": source}, list(
        dict.fromkeys(flags)
    )


def public_record(data: dict[str, Any]) -> dict[str, Any]:
    result = {k: v for k, v in data.items() if k != "raw"}
    flags = list(result.get("quality_flags") or [])
    for field in ("title", "company", "description", "location"):
        value = result.get(field)
        if isinstance(value, str) and field != "description":
            result[field] = value.strip()
        if not isinstance(value, str) or not value.strip():
            flags.append(field + "_missing")
    original = result.get("employment_type")
    result["employment_type"], unmapped = employment(original)
    result["employment_type_source"] = result.get("employment_type_source") or (
        original if original != result["employment_type"] else None
    )
    if unmapped:
        flags.append("employment_type_unmapped")
    original = result.get("remote_status")
    normalized = WORKPLACE.get(key(original)) if isinstance(original, str) else None
    result["remote_status"] = normalized or (
        original.strip() if isinstance(original, str) and original.strip() else None
    )
    result["remote_status_source"] = result.get("remote_status_source") or (
        original if original != result["remote_status"] else None
    )
    if original and normalized is None:
        flags.append("remote_status_unmapped")
    result["salary"], salary_flags = salary(result.get("salary"))
    flags.extend(salary_flags)
    published = result.get("published_at")
    if published:
        try:
            stamp = datetime.fromisoformat(published) if isinstance(published, str) else published
            if stamp.tzinfo is None:
                flags.append("publication_timezone_unspecified")
            else:
                result["published_at"] = stamp.astimezone(UTC).isoformat()
        except (ValueError, TypeError, AttributeError):
            result["published_at"] = None
            flags.append("publication_date_invalid")
    result["quality_flags"] = list(dict.fromkeys(flags))
    return result


def utc(stamp: datetime) -> datetime:
    return stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)


def public_job(
    job: Job, observations: list[Observation], *, description: bool = True
) -> dict[str, Any]:
    rows = [row for row in observations if row.job_id == job.id]
    active = [row for row in rows if row.status == "open"] or rows
    data = public_record(job.data)
    if not description:
        data.pop("description", None)
    return {
        "id": job.id,
        **data,
        "first_seen_at": min([utc(job.first_seen), *(utc(row.first_seen) for row in rows)]),
        "last_changed_at": max([utc(job.last_changed), *(utc(row.last_changed) for row in rows)]),
        "last_checked_at": max((utc(row.last_checked) for row in active), default=None),
        "sources": [
            {
                "source_id": row.source_id,
                "source_url": row.data["source_url"],
                "application_url": row.data["application_url"],
                "status": row.status,
                "first_seen_at": utc(row.first_seen),
                "last_changed_at": utc(row.last_changed),
                "last_checked_at": utc(row.last_checked),
            }
            for row in rows
        ],
    }
