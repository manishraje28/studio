import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator

from app.models import ProjectStatus

AnswerKey = Annotated[str, StringConstraints(min_length=1, max_length=60, pattern=r"^[a-z][a-z0-9_]*$")]
AnswerText = Annotated[str, StringConstraints(max_length=2000)]


class BriefIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    business_type: str = Field(min_length=2, max_length=80, examples=["café"])
    city: str | None = Field(default=None, max_length=80)
    website_url: HttpUrl | None = None
    # Flat text answers only (no nesting), capped so a brief cannot balloon storage or prompts.
    answers: dict[AnswerKey, AnswerText | list[AnswerText]] = Field(
        default_factory=dict,
        description="Brief chat answers, e.g. audience, tone, must-have pages, main call to action.",
    )

    @field_validator("answers")
    @classmethod
    def limit_answers(cls, v: dict[str, str | list[str]]) -> dict[str, str | list[str]]:
        if len(v) > 30:
            raise ValueError("at most 30 answers")
        if any(isinstance(a, list) and len(a) > 20 for a in v.values()):
            raise ValueError("at most 20 items per answer")
        return v


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    business_type: str
    city: str | None
    website_url: str | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent: str
    kind: str
    message: str
    data: dict[str, Any]
    created_at: datetime


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    version: int
    agent: str
    content: dict[str, Any]
    created_at: datetime


class DirectionDecision(BaseModel):
    decision: Literal["approve", "revise"]
    note: str | None = Field(default=None, max_length=1000, description="What to change, required for revise")
