import re

from pydantic import BaseModel, Field, model_validator

BANNED = [
    "elevate",
    "unleash",
    "seamless",
    "world-class",
    "cutting-edge",
    "revolutionize",
    "game-changer",
    "game changer",
    "unlock",
    "delve",
    "synergy",
    "tapestry",
    "embark",
    "nestled",
    "testament",
    "in today's fast-paced",
    "look no further",
    "second to none",
    "one-stop shop",
    "to perfection",
    "mouth-watering",
    "mouthwatering",
    "culinary journey",
    "like no other",
]
# Dashes used as punctuation: em dash anywhere, en dash or hyphen with spaces around it.
# Spaces and tabs only, never newlines, so "- item" bullet lists are left alone.
_DASH_RE = re.compile("[ \t]*—[ \t]*|[ \t]+[–-][ \t]+")


def plain_punctuation(text: str) -> str:
    """Turn dash-joined clauses into comma-joined ones. Hyphenated words are left alone."""
    return _DASH_RE.sub(", ", text)


_BANNED_RE = re.compile(r"\b(" + "|".join(re.escape(w) for w in BANNED) + r")\b", re.IGNORECASE)


class SectionCopy(BaseModel):
    section: str = Field(description="Which planned section this is, using the name from the sitemap")
    heading: str = Field(max_length=90)
    body: str = Field(max_length=900, description="Short paragraphs. Can be empty for a heading-only band.")
    cta_label: str | None = Field(default=None, max_length=30, description="Button text if this section has one")


class PageCopy(BaseModel):
    slug: str
    seo_title: str = Field(max_length=60)
    meta_description: str = Field(max_length=160)
    sections: list[SectionCopy] = Field(min_length=1, max_length=10)

    @model_validator(mode="before")
    @classmethod
    def fix_dashes(cls, data):
        # Models reach for dashes even when told not to; this is safer to fix in code than to argue about.
        if isinstance(data, dict):
            for key in ("seo_title", "meta_description"):
                if isinstance(data.get(key), str):
                    data[key] = plain_punctuation(data[key])
            for sec in data.get("sections") or []:
                if isinstance(sec, dict):
                    for key in ("heading", "body", "cta_label"):
                        if isinstance(sec.get(key), str):
                            sec[key] = plain_punctuation(sec[key])
        return data

    @model_validator(mode="after")
    def house_style(self) -> "PageCopy":
        text = " ".join(
            [self.seo_title, self.meta_description]
            + [f"{s.heading} {s.body} {s.cta_label or ''}" for s in self.sections]
        )
        problems = []
        if hits := sorted({m.group(0).lower() for m in _BANNED_RE.finditer(text)}):
            problems.append(f"uses banned hype words: {', '.join(hits)}; say it plainly")
        if problems:
            raise ValueError("; ".join(problems))
        return self
