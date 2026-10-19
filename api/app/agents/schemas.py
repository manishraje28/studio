from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Source = Literal["brief", "website", "general knowledge"]


class Fact(BaseModel):
    claim: str = Field(description="One specific statement about this business or its market.")
    source: Source = Field(
        description="Where it comes from. Use 'general knowledge' for typical patterns of this kind of business."
    )


class ResearchDossier(BaseModel):
    summary: str = Field(description="Three or four sentences on who the business is and what makes it worth visiting.")
    audiences: list[str] = Field(min_length=1, max_length=5, description="Distinct groups of likely customers.")
    what_customers_value: list[str] = Field(min_length=1, max_length=8)
    differentiators: list[str] = Field(max_length=6, description="What sets this business apart. Only if supported.")
    tone_words: list[str] = Field(min_length=2, max_length=6, description="Adjectives for the brand voice.")
    facts: list[Fact] = Field(max_length=15)
    open_questions: list[str] = Field(
        max_length=6, description="What we still need from the owner, e.g. opening hours, photos, prices."
    )


class PagePlan(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9-]*$", description="URL path without slashes; empty for the home page.")
    title: str
    goal: str = Field(description="What a visitor should do or learn on this page.")
    sections: list[str] = Field(min_length=2, max_length=8)


class PrimaryAction(BaseModel):
    label: str = Field(description="Button text, two to four words, e.g. 'Reserve a table'.")
    why: str


class Strategy(BaseModel):
    positioning: str = Field(description="One sentence: for whom, what, and why this business over others.")
    primary_audience: str
    primary_action: PrimaryAction
    messaging_pillars: list[str] = Field(min_length=3, max_length=3)
    pages: list[PagePlan] = Field(min_length=3, max_length=7)
    seo_keywords: list[str] = Field(min_length=3, max_length=10)


class PageLayout(BaseModel):
    slug: str
    blocks: list[str] = Field(description="One layout name per section, in order")

    @field_validator("blocks")
    @classmethod
    def known_layouts(cls, v: list[str]) -> list[str]:
        from app.site.render import LAYOUTS, LEGACY

        v = [LEGACY.get(b, b) for b in v]  # older names still mean something sensible
        if bad := [b for b in v if b not in LAYOUTS]:
            raise ValueError(f"unknown layouts {bad}; use only {LAYOUTS}")
        return v


class LayoutPlan(BaseModel):
    pages: list[PageLayout]


class GenericLine(BaseModel):
    page: str
    text: str = Field(description="The exact line from the copy")
    why: str = Field(description="Why it reads as generic or unsupported")
    suggestion: str = Field(description="A more specific rewrite using facts from the research")


class CopyReview(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def plain_dashes(cls, data):
        from app.agents.copywriting import plain_punctuation

        if isinstance(data, dict):
            if isinstance(data.get("summary"), str):
                data["summary"] = plain_punctuation(data["summary"])
            for line in data.get("generic_lines") or []:
                if isinstance(line, dict):
                    for k in ("why", "suggestion"):
                        if isinstance(line.get(k), str):
                            line[k] = plain_punctuation(line[k])
        return data

    specificity: int = Field(ge=0, le=10, description="10 = could only be this business; 0 = could be any business")
    summary: str = Field(description="Two sentences for the owner")
    generic_lines: list[GenericLine] = Field(max_length=6)


PEOPLE_WORDS = {"woman", "women", "man", "men", "person", "people", "girl", "boy", "model", "face", "bride", "customer"}


class PhotoQueries(BaseModel):
    queries: list[str] = Field(min_length=3, max_length=6)

    @field_validator("queries")
    @classmethod
    def no_people(cls, v: list[str]) -> list[str]:
        clean = [q.strip()[:60] for q in v if q.strip()]
        if bad := [q for q in clean if set(q.lower().split()) & PEOPLE_WORDS]:
            raise ValueError(f"no people in photo searches: {bad}")
        return clean
