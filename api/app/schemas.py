import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models import ProjectStatus


class BriefIn(BaseModel):
    business_name: str = Field(min_length=2, max_length=160)
    business_type: str = Field(min_length=2, max_length=80, examples=["café"])
    city: str | None = Field(default=None, max_length=80)
    website_url: HttpUrl | None = None
    answers: dict[str, Any] = Field(
        default_factory=dict,
        description="Brief chat answers, e.g. audience, tone, must-have pages, main call to action.",
    )


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
