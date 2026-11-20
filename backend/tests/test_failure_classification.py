import pytest

from scripts.production_review import failure_category


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("HTTP 429 fetching robots.txt", "rate_limited"),
        ("Career page robots policy disallows this request", "robots_disallowed"),
        ("Worker stopped before refresh finished", "deployment_interruption"),
        ("Publisher identity mismatch", "publisher_identity_mismatch"),
        ("Missing unique public career bootstrap", "native_schema_changed"),
        ("Native and structured descriptions disagree", "description_validation"),
        ("Search and sitemap do not agree", "incomplete_enumeration"),
    ],
)
def test_classifies_operational_failures_without_mistaking_rate_limit_for_policy(message, expected):
    assert failure_category(message) == expected
