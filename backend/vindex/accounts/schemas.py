from datetime import datetime
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator

from vindex.schemas import JobOut

Term = Annotated[str, Field(min_length=1, max_length=100)]


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


def check_new_password(value: SecretStr) -> SecretStr:
    password = value.get_secret_value()
    if len(password) < 15 or password.isspace():
        raise ValueError("Use a password with 15 to 128 characters")
    return value


class Registration(Credentials):
    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        return check_new_password(value)


class EmailCode(BaseModel):
    code: str = Field(pattern=r"^[0-9]{8}$")


class PasswordConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(min_length=1, max_length=128)


class PasswordChange(PasswordConfirmation):
    new_password: SecretStr = Field(min_length=15, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        return check_new_password(value)


class AccountOut(BaseModel):
    id: str
    email: str
    email_verified: bool = False
    created_at: datetime


ProfileEntry = Annotated[str, Field(min_length=1, max_length=1000)]


class ProfessionalLink(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: Term
    url: str = Field(max_length=2048)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if any(c.isspace() or ord(c) < 32 or c == chr(92) for c in value):
            raise ValueError("Expected a professional HTTPS URL")
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise ValueError("Expected a professional HTTPS URL")
        return value


class ProfileHighlights(BaseModel):
    education: list[ProfileEntry] = Field(default_factory=list, max_length=30)
    experience: list[ProfileEntry] = Field(default_factory=list, max_length=30)
    projects: list[ProfileEntry] = Field(default_factory=list, max_length=30)
    links: list[ProfessionalLink] = Field(default_factory=list, max_length=12)


class ResumeSuggestions(ProfileHighlights):
    full_name: str = Field(default="", max_length=100)
    headline: str = Field(default="", max_length=160)
    bio: str = Field(default="", max_length=2000)


class ProfileInput(ProfileHighlights):
    model_config = ConfigDict(extra="forbid")
    full_name: str = Field(default="", max_length=100)
    headline: str = Field(default="", max_length=160)
    location: str = Field(default="", max_length=100)
    bio: str = Field(default="", max_length=2000)
    desired_titles: list[Term] = Field(default_factory=list, max_length=20)
    skills: list[Term] = Field(default_factory=list, max_length=50)
    preferred_locations: list[Term] = Field(default_factory=list, max_length=10)
    remote_only: bool = False
    use_resume_skills: bool = True
    experience_years: int | None = Field(default=None, ge=0, le=60)


class ProfileOut(ProfileInput):
    updated_at: datetime | None = None


class ResumeOut(BaseModel):
    filename: str
    media_type: str
    size_bytes: int
    text_characters: int
    detected_skills: list[str]
    suggestions: ResumeSuggestions = Field(default_factory=ResumeSuggestions)
    updated_at: datetime


class RecommendationItem(BaseModel):
    job: JobOut
    rank_score: int
    reasons: list[str]


class RecommendationsOut(BaseModel):
    items: list[RecommendationItem]
    total_candidates: int
    candidates_ranked: int
    candidate_limit: int = 1000
    truncated: bool
    limit: int
    offset: int
    needs_preferences: bool = False
    method: str = (
        "Explicit role/skill matches; rank scores are ordering signals, not fit percentages"
    )
