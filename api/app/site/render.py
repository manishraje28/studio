"""Turn approved artifacts (style, copy, layout plan, photos, details) into static HTML pages.

The model never writes markup. It only chooses a layout per section; this module renders
with autoescaping, so copy cannot inject HTML or scripts into the client's site.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, quote_plus

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

# How many photos each block can use. Blocks that need a photo fall back when none is left.
PHOTO_SLOTS = {"hero_image": 1, "hero_split": 1, "hero_editorial": 2, "story": 1, "services": 3, "gallery": 6}
LAYOUTS = [
    "hero_image",
    "hero_split",
    "hero_editorial",
    "story",
    "services",
    "price_list",
    "gallery",
    "quote_band",
    "cta_band",
    "steps",
    "faq",
    "contact",
    "text",
]
# Plans written before the richer block set still render.
LEGACY = {"hero_center": "hero_editorial", "cards": "services", "list": "services"}
FALLBACK = {"hero_image": "hero_split", "hero_editorial": "hero_split", "gallery": "text"}

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["j2", "html"], default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)

_BULLET = re.compile(r"^([-*•]|\d+[.)])\s")
_PRICE = re.compile(
    r"((?:₹|Rs\.?|INR|\$|€|£)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:onwards|\+))?|\d[\d,]*\s?(?:rs|rupees|/-))", re.I
)


def _placeholders(text: str) -> Markup:
    """Escape, then wrap [details we still need] so the owner can spot them in the preview."""
    return Markup(re.sub(r"\[([^\[\]]{1,80})\]", r'<span class="ph">[\1]</span>', str(escape(text or ""))))


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n|\n", text or "") if p.strip()]


def _items(text: str) -> dict:
    """Split a body into an intro line and list items (bullets, or one sentence per item)."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    bullets = [_BULLET.sub("", ln) for ln in lines if _BULLET.match(ln)]
    if bullets:
        return {"lead": " ".join(ln for ln in lines if not _BULLET.match(ln)), "entries": bullets}
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text or "") if s.strip()]
    return {"lead": "", "entries": sentences}


def _split_item(text: str) -> dict:
    """'Bridal makeup: full look with trial. ₹4,500' -> title, text, price."""
    price = None
    if m := _PRICE.search(text):
        price = m.group(1).strip()
        text = (text[: m.start()] + text[m.end() :]).strip(" .,-:")
    if m := re.match(r"^([^:.–]{2,48})[:–]\s*(.+)$", text):
        return {"title": m.group(1).strip(), "text": m.group(2).strip(), "price": price}
    if len(text) <= 48:
        return {"title": text, "text": "", "price": price}
    return {"title": "", "text": text, "price": price}


def _faq(text: str) -> list[dict]:
    """Questions end with '?'; whatever follows until the next question is the answer."""
    parts = re.split(r"(?<=\?)\s+", (text or "").strip())
    out, current = [], None
    for chunk in parts:
        for line in [ln.strip() for ln in _BULLET.sub("", chunk).splitlines() if ln.strip()]:
            if line.endswith("?"):
                current = {"q": re.sub(r"^(Q[:.]\s*)", "", line), "a": ""}
                out.append(current)
            elif current is not None:
                current["a"] = (current["a"] + " " + re.sub(r"^(A[:.]\s*)", "", line)).strip()
    return out or [{"q": p, "a": ""} for p in _paragraphs(text)]


def _contact(text: str) -> dict:
    """Lines like 'Phone: [phone number]' become a definition list; the rest stays as text."""
    pairs, rest = [], []
    for ln in _paragraphs(text):
        m = re.match(r"^([A-Za-z][A-Za-z /&]{1,24}):\s*(.+)$", _BULLET.sub("", ln))
        (pairs.append((m.group(1), m.group(2))) if m else rest.append(ln))
    return {"pairs": pairs, "text": rest}


def _humanize(name: str) -> str:
    return re.sub(r"[_-]+", " ", name or "").strip().capitalize()


_LABEL_NOISE = {
    "brief",
    "overview",
    "snippet",
    "section",
    "block",
    "intro",
    "introduction",
    "cta",
    "of",
    "the",
    "with",
    "and",
    "short",
    "main",
    "primary",
    "details",
    "info",
    "information",
    "list",
    "grid",
}


def _label(name: str) -> str:
    """A short section label for the eyebrow text, or nothing if the planner's name is internal jargon."""
    words = [w for w in re.split(r"[\s_-]+", (name or "").lower()) if w and w not in _LABEL_NOISE]
    return " ".join(words).capitalize() if 0 < len(words) <= 2 else ""


_env.filters.update(
    placeholders=_placeholders,
    paragraphs=_paragraphs,
    items=_items,
    contact=_contact,
    split_item=_split_item,
    faq=_faq,
    humanize=_humanize,
    label=_label,
)
_env.globals["range"] = range


@dataclass
class SitePage:
    slug: str
    nav_label: str


def fonts_url(heading: str, body: str) -> str:
    fam = [
        f"family={quote(f).replace('%20', '+')}:ital,wght@0,400;0,500;0,600;0,700;1,400"
        for f in dict.fromkeys([heading, body])
    ]
    return "https://fonts.googleapis.com/css2?" + "&".join(fam) + "&display=swap"


def favicon_svg(letter: str, bg: str, fg: str) -> str:
    letter = escape(letter[:1].upper() or "S")
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' "
        f"fill='{bg}'/><text x='16' y='22' text-anchor='middle' font-family='Georgia,serif' font-size='18' "
        f"font-weight='700' fill='{fg}'>{letter}</text></svg>"
    )


def look_for(heading_style: str) -> dict:
    """Shape language that follows the art director's heading style."""
    return {
        "italic accents": {"radius": "18px", "frame": "14px", "heading_weight": "500", "tracking": "-0.015em"},
        "tight and heavy": {"radius": "2px", "frame": "10px", "heading_weight": "800", "tracking": "-0.035em"},
        "all caps small": {"radius": "0px", "frame": "12px", "heading_weight": "600", "tracking": "-0.01em"},
    }.get(heading_style, {"radius": "10px", "frame": "12px", "heading_weight": "600", "tracking": "-0.02em"})


def contact_links(values: dict[str, str], contact_url: str) -> dict:
    """Turn the owner's details into working links. Unknown or empty details simply do not appear."""

    def pick(*words: str) -> str:
        for key, val in values.items():
            if val and any(w in key.lower() for w in words):
                return val.strip()
        return ""

    phone = pick("whatsapp", "phone", "mobile", "contact number")
    digits = re.sub(r"\D", "", phone)
    wa_digits = ("91" + digits) if len(digits) == 10 else digits
    address = pick("address", "location")
    email = pick("email")
    return {
        "phone": phone if len(digits) >= 8 else "",
        "phone_digits": ("+" + wa_digits) if digits else "",
        "whatsapp": f"https://wa.me/{wa_digits}" if len(digits) >= 10 else "",
        "email": email if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) else "",
        "address": address,
        "maps": f"https://www.google.com/maps/search/?api=1&query={quote_plus(address)}" if address else "",
        "hours": pick("hour", "timing", "open"),
        "social": pick("instagram", "social", "facebook"),
        "primary_href": contact_url,
    }


def render_site(
    *,
    business_name: str,
    business_type: str,
    city: str | None,
    strategy: dict,
    style: dict,
    copy: dict,
    layout: dict,
    url_for,
    photos: list[dict] | None = None,
    details: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return {slug: html}. url_for(slug) builds links, so preview and export can differ."""
    pages_plan = strategy["pages"]
    copy_by_slug = {p["slug"]: p for p in copy["pages"]}
    layout_by_slug = {p["slug"]: p["blocks"] for p in layout["pages"]}
    contact_slug = next((p["slug"] for p in pages_plan if re.search(r"contact|visit|book|order|find", p["slug"])), None)
    contact_url = (url_for(contact_slug) if contact_slug is not None else "") + "#contact"
    pool = [p for p in (photos or []) if p.get("url")]
    site = {
        "business_name": business_name,
        "business_type": business_type,
        "city": city,
        "primary_action": strategy["primary_action"]["label"],
        "signature": (style.get("signature_ideas") or [{}])[0].get("name"),
        "pages": [SitePage(p["slug"], "Home" if not p["slug"] else p["title"]) for p in pages_plan],
    }
    p, t = style["palette"], style["typography"]
    common = {
        "site": site,
        "p": p,
        "t": t,
        "look": look_for(t.get("heading_style", "regular")),
        "url": url_for,
        "fonts_url": fonts_url(t["heading_font"], t["body_font"]),
        "favicon": favicon_svg(business_name, p["accent"], p["accent_ink"]),
        "year": datetime.now(UTC).year,
        "contact": contact_links(details or {}, contact_url),
        "og_image": pool[0]["url"] if pool and pool[0]["url"].startswith("https://") else None,
    }
    template = _env.get_template("page.html.j2")
    out = {}
    for plan in pages_plan:
        page = copy_by_slug.get(plan["slug"])
        if page is None:
            continue
        chosen = layout_by_slug.get(plan["slug"], [])
        # Every page starts its photo rotation at a different point so pages do not repeat the same image.
        cursor = (len(out) * 3) % len(pool) if pool else 0
        blocks, used = [], []
        for i, section in enumerate(page["sections"]):
            name = chosen[i] if i < len(chosen) else ("hero_split" if i == 0 else "text")
            name = LEGACY.get(name, name)
            if name not in LAYOUTS:
                name = "hero_split" if i == 0 else "text"
            want = PHOTO_SLOTS.get(name, 0)
            # Image-led blocks need enough photos; otherwise use their text-led sibling.
            if name in ("hero_image", "gallery") and len(pool) < (1 if name == "hero_image" else 3):
                name = FALLBACK[name]
                want = PHOTO_SLOTS.get(name, 0)
            if name == "hero_editorial" and len(pool) < 2:
                name, want = "hero_split", 1
            if name == "services":
                # All cards get a photo or none do; a half-illustrated grid looks broken.
                n = len(_items(section.get("body", ""))["entries"])
                want = n if 0 < n <= 4 and len(pool) >= n + 2 else 0
            taken = []
            for _ in range(min(want, len(pool))):
                taken.append(pool[cursor % len(pool)])
                cursor += 1
            used += taken
            blocks.append({"layout": name, "section": section, "photos": taken})
        credits = list(dict.fromkeys(ph["credit"] for ph in used if ph.get("credit")))
        out[plan["slug"]] = template.render(page=page, blocks=blocks, credits=credits, **common)
    return out
