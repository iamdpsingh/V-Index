"""Bounded diagnostic categories; never emit raw source or credential-bearing errors."""


def failure_category(message: str) -> str:
    message = message.lower()
    for term, label in [
        ("429", "rate_limited"),
        ("robots policy disallows", "robots_disallowed"),
        ("robots", "robots_fetch_failure"),
        ("404", "native_route_missing"),
        ("403", "access_denied"),
        ("301", "native_redirect"),
        ("worker stopped", "deployment_interruption"),
        ("identity mismatch", "publisher_identity_mismatch"),
        ("description", "description_validation"),
        ("sitemap", "incomplete_enumeration"),
        ("disagree", "incomplete_enumeration"),
        ("bootstrap", "native_schema_changed"),
        ("unexpected paradox page", "native_schema_changed"),
        ("timeout", "timeout"),
        ("pagination", "incomplete_enumeration"),
        ("enumeration", "incomplete_enumeration"),
        ("externalpath", "native_schema_changed"),
    ]:
        if term in message:
            return label
    return "unclassified_fetch_failure"
