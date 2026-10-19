"""Art direction output and the deterministic checks that keep it honest.

The model proposes; these validators decide. A failed check raises, which sends the model
one repair round with the exact error (see LLMClient.complete_json).
"""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Google Fonts we know load well and render well at display and body sizes.
HEADING_FONTS = [
    "Fraunces",
    "Playfair Display",
    "DM Serif Display",
    "Libre Caslon Text",
    "Cormorant Garamond",
    "Instrument Serif",
    "Young Serif",
    "Bricolage Grotesque",
    "Space Grotesk",
    "Syne",
    "Archivo",
    "Sora",
    "Outfit",
    "Unbounded",
    "Gloock",
    "Bodoni Moda",
]
BODY_FONTS = [
    "Inter Tight",
    "Inter",
    "DM Sans",
    "Work Sans",
    "Manrope",
    "Source Sans 3",
    "IBM Plex Sans",
    "Public Sans",
    "Karla",
    "Nunito Sans",
    "Libre Franklin",
    "Lora",
    "Source Serif 4",
]

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def _luminance(hex_color: str) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _is_purple(hex_color: str) -> bool:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    # Saturated violet/indigo: blue strongest, red well above green. The "AI startup" look.
    return b > 120 and b > g + 40 and r > g + 20 and max(r, g, b) - min(r, g, b) > 60


class Palette(BaseModel):
    background: str = Field(description="Page background, hex like #f4ece1")
    surface: str = Field(description="Cards and panels, close to the background")
    ink: str = Field(description="Main text colour")
    muted: str = Field(description="Secondary text colour")
    accent: str = Field(description="Buttons and key highlights")
    accent_ink: str = Field(description="Text colour used on top of the accent")

    @field_validator("*")
    @classmethod
    def is_hex(cls, v: str) -> str:
        if not HEX.match(v):
            raise ValueError(f"{v!r} is not a 6-digit hex colour like #1a2b3c")
        return v.lower()

    @model_validator(mode="after")
    def readable(self) -> "Palette":
        checks = [
            ("ink on background", self.ink, self.background, 7.0),
            ("ink on surface", self.ink, self.surface, 7.0),
            ("muted on background", self.muted, self.background, 4.5),
            ("accent_ink on accent", self.accent_ink, self.accent, 4.5),
            ("accent on background", self.accent, self.background, 3.0),
        ]
        problems = [
            f"{name} contrast is {contrast(fg, bg):.2f}, needs at least {need}"
            for name, fg, bg, need in checks
            if contrast(fg, bg) < need
        ]
        if any(_is_purple(c) for c in (self.accent, self.background, self.surface)):
            problems.append("purple or violet accents and backgrounds read as generic AI design; choose another hue")
        if problems:
            raise ValueError("; ".join(problems))
        return self


class Typography(BaseModel):
    heading_font: str = Field(description=f"One of: {', '.join(HEADING_FONTS)}")
    body_font: str = Field(description=f"One of: {', '.join(BODY_FONTS)}")
    heading_style: Literal["regular", "italic accents", "all caps small", "tight and heavy"]
    why: str

    @field_validator("heading_font")
    @classmethod
    def known_heading(cls, v: str) -> str:
        if v not in HEADING_FONTS:
            raise ValueError(f"heading_font must be one of {HEADING_FONTS}")
        return v

    @field_validator("body_font")
    @classmethod
    def known_body(cls, v: str) -> str:
        if v not in BODY_FONTS:
            raise ValueError(f"body_font must be one of {BODY_FONTS}")
        return v


class SignatureIdea(BaseModel):
    name: str = Field(description="Short name, e.g. 'Menu as a library card'")
    description: str = Field(description="What it looks like on the page and where it appears")
    why_it_fits: str = Field(description="Which fact from the research it comes from")


class StyleTile(BaseModel):
    mood: str = Field(description="Two sentences on how the site should feel, specific to this business")
    palette: Palette
    typography: Typography
    signature_ideas: list[SignatureIdea] = Field(min_length=1, max_length=2)
    imagery: str = Field(description="What photos to use. Prefer the owner's real photos; no stock people.")
    layout_notes: list[str] = Field(min_length=2, max_length=5)
    avoid: list[str] = Field(min_length=2, max_length=6, description="Things this design must not do")
