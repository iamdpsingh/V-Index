"""Conservative resume suggestions based on explicit section headings."""

import re
from urllib.parse import urlsplit

from pydantic import ValidationError

from vindex.accounts.schemas import ProfessionalLink, ProfileHighlights

HEADINGS = {
    "education": "education",
    "academic background": "education",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment history": "experience",
    "projects": "projects",
    "personal projects": "projects",
    "selected projects": "projects",
    "skills": "",
    "technical skills": "",
    "summary": "",
    "certifications": "",
    "awards": "",
    "volunteer experience": "",
    "interests": "",
    "languages": "",
}
URL_PATTERN = re.compile(r"""https://[^\s<>"']+""", re.IGNORECASE)


def suggest_profile(text: str) -> ProfileHighlights:
    entries: dict[str, list[str]] = {"education": [], "experience": [], "projects": []}
    section = ""
    for line in text.splitlines():
        line = line.strip()
        heading = line.rstrip(":").casefold()
        if heading in HEADINGS:
            section = HEADINGS[heading]
        elif section and line and len(entries[section]) < 30:
            entries[section].append(line[:1000])

    links: list[ProfessionalLink] = []
    for value in dict.fromkeys(m.group().rstrip(".,);]}") for m in URL_PATTERN.finditer(text)):
        if len(links) == 12:
            break
        try:
            host = (urlsplit(value).hostname or "").removeprefix("www.")
            label = {"linkedin.com": "LinkedIn", "github.com": "GitHub"}.get(host, "Website")
            links.append(ProfessionalLink(label=label, url=value))
        except (ValidationError, ValueError):
            continue
    return ProfileHighlights(**entries, links=links)
