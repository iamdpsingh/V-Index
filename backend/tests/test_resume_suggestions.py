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
