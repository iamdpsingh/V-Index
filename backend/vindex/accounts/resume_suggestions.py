"""Conservative resume suggestions based on explicit section headings."""

import re
from urllib.parse import urlsplit

from pydantic import ValidationError

from vindex.accounts.schemas import ProfessionalLink, ResumeSuggestions

HEADINGS = {
    "education": "education",
    "education and qualifications": "education",
    "educational qualifications": "education",
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
    "project": "projects",
    "technical projects": "projects",
    "key projects": "projects",
    "personal projects": "projects",
    "selected projects": "projects",
    "project work": "projects",
    "academic projects": "projects",
    "project experience": "projects",
    "skills": "",
    "achievements": "",
    "publications": "",
    "references": "",
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


BULLET = re.compile(r"^[•▪◦●‣–—*-]\s*|^\d{1,2}[.)]\s+")
INLINE_BULLET = re.compile(r"\s+[•▪◦●‣]\s+|\s+(?=\d{1,2}[.)]\s+[A-Z])")
QUALIFICATION = re.compile(
    r"^(?:class|grade|standard|std\.?)\s*(?:xii|xi|x|ix|12(?:th)?|11(?:th)?|10(?:th)?|9(?:th)?)\b"
    r"|^(?:10th|12th)\b|^(?:xii|x)(?=\s*[|()–—-]|$)"
    r"|^(?:higher secondary|senior secondary|secondary school|secondary education|high school|"
    r"highschool|intermediate|matriculation|ssc|hsc|sslc|cbse|icse|isc|"
    r"bachelor|master|diploma|ph\.?d\.?|b\.?sc\.?|m\.?sc\.?|b\.?tech\.?|m\.?tech\.?|"
    r"b\.?e\.?|bca|mca|bba|mba)\b",
    re.IGNORECASE,
)
DETAIL = re.compile(
    r"^(?:built|created|developed|designed|implemented|deployed|used|integrated|led|"
    r"improved|automated|reduced|increased|worked|managed|delivered|engineered|"
    r"description|tech stack|technologies|tools|github|demo|cgpa|gpa|percentage|score)\b",
    re.IGNORECASE,
)


def add_entry(section: str, entries: list[str], line: str, marked: bool) -> None:
    continuation = False
    if entries and section == "education":
        continuation = not QUALIFICATION.match(line) and (bool(DETAIL.match(line)) or not marked)
    elif entries and section in {"experience", "projects"}:
        continuation = bool(DETAIL.match(line))
    if continuation:
        entries[-1] = f"{entries[-1]}\n{line}"[:1000]
    elif len(entries) < 30:
        entries.append(line[:1000])


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
    for raw in text.splitlines():
        line = raw.strip()
        marked = bool(BULLET.match(line))
        line = BULLET.sub("", line, count=1).strip()
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
        if section and line and not URL_PATTERN.fullmatch(line):
            parts = INLINE_BULLET.split(line) if section in {"education", "projects"} else [line]
            for index, part in enumerate(parts):
                part = BULLET.sub("", part, count=1).strip()
                if part and not URL_PATTERN.fullmatch(part):
                    add_entry(section, entries[section], part, marked or index > 0)

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
