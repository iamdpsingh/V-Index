"""Bounded diagnostic categories; never emit raw source or credential-bearing errors."""

import re


def failure_category(message: str) -> str:
    message = message.lower()
    status = re.search(r"(?:\bhttp\s+|error\s+['\"])([1-5][0-9]{2})\b", message)
    if status:
        code = int(status.group(1))
        known = {
            301: "native_redirect",
            401: "access_denied",
            403: "access_denied",
            404: "native_route_missing",
            429: "rate_limited",
        }
        if code in known:
            return known[code]
        if code >= 500:
            return "upstream_server_error"
    for term, label in [
        ("robots policy disallows", "robots_disallowed"),
        ("robots", "robots_fetch_failure"),
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
