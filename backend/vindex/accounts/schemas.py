from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr

from vindex.schemas import JobOut

Term = Annotated[str, Field(min_length=1, max_length=100)]


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    password: SecretStr = Field(min_length=12, max_length=128)


class PasswordConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(min_length=1, max_length=128)


class PasswordChange(PasswordConfirmation):
    new_password: SecretStr = Field(min_length=12, max_length=128)


class AccountOut(BaseModel):
    id: str
    email: str
    email_verified: bool = False
    created_at: datetime


class ProfileInput(BaseModel):
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
