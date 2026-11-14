import pytest
from pydantic import ValidationError
from vindex.accounts.resume_suggestions import suggest_profile
from vindex.accounts.schemas import ProfessionalLink


def test_explicit_resume_sections_and_links():
    result = suggest_profile(
        "Education:\nBSc Computing\nWork Experience\nEngineer, 2022–2025\n"
        "Projects\nSearch index\nSkills\nPython\nhttps://github.com/example."
    )
    assert result.education == ["BSc Computing"]
    assert result.experience == ["Engineer, 2022–2025"]
    assert result.projects == ["Search index"]
    assert result.links == [ProfessionalLink(label="GitHub", url="https://github.com/example")]


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "https://name@example.com", "https://example.com:80"]
)
def test_professional_links_reject_unsafe_schemes_credentials_and_ports(url):
    with pytest.raises(ValidationError):
        ProfessionalLink(label="Website", url=url)


def test_resume_header_and_professional_summary_suggestions():
    result = suggest_profile(
        "Asha Mehta\nSenior Data Engineer\nasha@example.com\n"
        "Professional Summary: Builds reliable data pipelines.\n"
        "Leads migration projects.\nEducation\nBSc Computing"
    )
    assert result.full_name == "Asha Mehta"
    assert result.headline == "Senior Data Engineer"
    assert result.bio == "Builds reliable data pipelines. Leads migration projects."
    assert result.education == ["BSc Computing"]


def test_resume_without_identity_does_not_suggest_a_section_title():
    result = suggest_profile("Work Experience\nSenior Data Engineer\nProjects\nIndexer")
    assert (result.full_name, result.headline, result.bio) == ("", "", "")


def test_projects_keep_descriptions_with_separate_numbered_and_inline_entries():
    result = suggest_profile(
        "Technical Projects\n"
        "1. Rolewisp Indexer\n"
        "• Built a pipeline for job listings.\n"
        "Tech stack: Python and PostgreSQL\n"
        "2. Campus Navigator • Weather Dashboard\n"
        "Developed a forecast display.\n"
    )
    assert result.projects == [
        "Rolewisp Indexer\nBuilt a pipeline for job listings.\nTech stack: Python and PostgreSQL",
        "Campus Navigator",
        "Weather Dashboard\nDeveloped a forecast display.",
    ]


def test_school_qualifications_keep_school_and_dates_with_entry():
    result = suggest_profile(
        "Educational Qualifications\n"
        "B.Tech in Computer Science\nUniversity of Example\n2022–2026\n"
        "Intermediate (Class XII) | Example Junior College | 2022\n"
        "High School (Class X)\nExample High School\n"
        "Class IX | Earlier School\n"
    )
    assert result.education == [
        "B.Tech in Computer Science\nUniversity of Example\n2022–2026",
        "Intermediate (Class XII) | Example Junior College | 2022",
        "High School (Class X)\nExample High School",
        "Class IX | Earlier School",
    ]
