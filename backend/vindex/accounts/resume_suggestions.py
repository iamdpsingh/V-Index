"""Conservative resume suggestions based on explicit section headings."""

import re
from urllib.parse import urlsplit

from pydantic import ValidationError

from vindex.accounts.schemas import ProfessionalLink, ResumeSuggestions

HEADINGS = {
    "education": "education",
    "academic background": "education",
    "academic qualifications": "education",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment history": "experience",
    "work history": "experience",
    "career history": "experience",
    "internships": "experience",
    "projects": "projects",
    "personal projects": "projects",
    "selected projects": "projects",
    "academic projects": "projects",
    "project experience": "projects",
    "skills": "",
    "technical skills": "",
    "summary": "bio",
    "professional summary": "bio",
    "career summary": "bio",
    "about me": "bio",
    "profile": "bio",
    "certifications": "",
    "awards": "",
    "volunteer experience": "",
    "interests": "",
    "languages": "",
}
URL_PATTERN = re.compile(r"""https://[^\s<>"']+""", re.IGNORECASE)


ROLE = re.compile(
    r"\b(engineer|developer|analyst|designer|manager|consultant|specialist|researcher|"
    r"architect|scientist|director|recruiter|accountant|writer|student|intern|"
    r"coordinator|administrator|technician|lead)\b",
    re.IGNORECASE,
)


def name_candidate(line: str) -> bool:
    words = line.split()
    return (
        2 <= len(words) <= 5
        and len(line) <= 100
        and all(
            term.strip(".'’-").isalpha() and all(c.isalpha() or c in ".'’-" for c in term)
            for term in words
        )
        and not ROLE.search(line)
        and not any(
            word.casefold() in {"resume", "curriculum", "vitae", "portfolio"} for word in words
        )
    )


def suggest_profile(text: str) -> ResumeSuggestions:
    entries: dict[str, list[str]] = {"education": [], "experience": [], "projects": [], "bio": []}
    full_name = ""
    headline = ""
    in_header = True
    header_lines = 0
    section = ""
    for line in text.splitlines():
        line = line.strip().lstrip("•▪◦").strip()
        if not line:
            continue
        name, delimiter, content = line.partition(":")
        heading = name.strip().casefold()
        if heading in HEADINGS:
            in_header = False
            section = HEADINGS[heading]
            line = content.strip() if delimiter else ""
        elif in_header and header_lines < 8:
            header_lines += 1
            if heading in {"name", "full name"} and delimiter and name_candidate(content.strip()):
                full_name = content.strip()
            elif not full_name and header_lines <= 3 and name_candidate(line):
                full_name = line
            if (
                not headline
                and len(line) <= 160
                and "@" not in line
                and not URL_PATTERN.search(line)
                and (
                    (
                        heading in {"headline", "professional headline", "job title"}
                        and delimiter
                        and content.strip()
                    )
                    or (
                        full_name
                        and line != full_name
                        and len(line.split()) <= 10
                        and ROLE.search(line)
                    )
                )
            ):
                headline = (
                    content.strip()
                    if delimiter and heading in {"headline", "professional headline", "job title"}
                    else line
                )
        if section and line and not URL_PATTERN.fullmatch(line) and len(entries[section]) < 30:
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
    bio = " ".join(entries.pop("bio"))
    bio = URL_PATTERN.sub("", re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "", bio))
    return ResumeSuggestions(
        **entries, links=links, full_name=full_name, headline=headline, bio=bio.strip()[:2000]
    )
