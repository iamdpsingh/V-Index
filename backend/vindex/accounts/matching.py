"""Transparent professional-term ranking; no external models or personal-trait inference."""

import re

KNOWN_SKILLS = (
    "Python",
    "SQL",
    "JavaScript",
    "TypeScript",
    "Java",
    "C++",
    "C#",
    ".NET",
    "Rust",
    "React",
    "Next.js",
    "Vue",
    "Angular",
    "FastAPI",
    "Django",
    "Flask",
    "Node.js",
    "PostgreSQL",
    "MySQL",
    "Redis",
    "MongoDB",
    "Docker",
    "Kubernetes",
    "AWS",
    "Azure",
    "GCP",
    "Airflow",
    "Spark",
    "Kafka",
    "dbt",
    "Snowflake",
    "Databricks",
    "Terraform",
    "Linux",
    "Git",
    "Tableau",
    "Power BI",
    "Excel",
    "Figma",
    "Salesforce",
    "HubSpot",
    "Accounting",
    "Recruiting",
    "Project Management",
    "Product Management",
    "Data Analysis",
    "Machine Learning",
)


def contains(text: str, term: str) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(term.strip()) + r"(?!\w)", text, re.I))


def detected_skills(text: str) -> list[str]:
    # Contact addresses/URLs are not evidence of professional skills.
    text = re.sub(r"https?://\S+|[\w.+-]+@[\w.-]+", " ", text)
    result = [skill for skill in KNOWN_SKILLS if contains(text, skill)]
    if contains(text, "Golang"):
        result.append("Go")
    return result


def unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        term = value.strip()
        if term and term.casefold() not in seen:
            seen.add(term.casefold())
            result.append(term)
    return result
