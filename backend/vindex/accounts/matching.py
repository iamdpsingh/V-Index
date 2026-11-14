"""Transparent professional-term ranking; no external models or personal-trait inference."""

import re


def contains(text: str, term: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(term.strip()) + r"(?!\w)", text, re.I))


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        term = value.strip()
        if term and term.casefold() not in seen:
            seen.add(term.casefold())
            result.append(term)
    return result
