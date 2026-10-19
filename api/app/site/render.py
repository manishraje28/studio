"""Turn approved artifacts (style, copy, layout plan) into static HTML pages.

The model never writes markup. It only chooses a layout per section; this module renders
with autoescaping, so copy cannot inject HTML or scripts into the client's site.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

LAYOUTS = ["hero_split", "hero_center", "text", "cards", "list", "steps", "cta_band", "contact"]

_env = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(["j2", "html"], default=True),
    trim_blocks=True,
    lstrip_blocks=True,
)


def _placeholders(text: str) -> Markup:
    """Escape, then wrap [details we still need] so the owner can spot them in the preview."""
    return Markup(re.sub(r"\[([^\[\]]{1,80})\]", r'<span class="ph">[\1]</span>', str(escape(text or ""))))


def _paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n|\n", text or "") if p.strip()]


def _items(text: str) -> dict:
    """Split a body into an intro line and list items (bullets, or one sentence per item)."""
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    bullets = [re.sub(r"^[-*•]\s*|^\d+[.)]\s*", "", ln) for ln in lines if re.match(r"^([-*•]|\d+[.)])\s", ln)]
    if bullets:
        intro = " ".join(ln for ln in lines if not re.match(r"^([-*•]|\d+[.)])\s", ln))
        return {"lead": intro, "entries": bullets}
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+|,\s+(?=[A-Z])", text or "") if s.strip()]
    return {"lead": "", "entries": sentences}


def _contact(text: str) -> dict:
    """Lines like 'Phone: [phone number]' become a definition list; the rest stays as text."""
    pairs, rest = [], []
    for ln in _paragraphs(text):
        m = re.match(r"^([A-Za-z][A-Za-z /&]{1,24}):\s*(.+)$", ln)
        (pairs.append((m.group(1), m.group(2))) if m else rest.append(ln))
    return {"pairs": pairs, "text": rest}


_env.filters.update(placeholders=_placeholders, paragraphs=_paragraphs, items=_items, contact=_contact)
_env.globals["range"] = range


@dataclass
class SitePage:
    slug: str
    nav_label: str


def fonts_url(heading: str, body: str) -> str:
    fam = [f"family={quote(f).replace('%20', '+')}:ital,wght@0,400;0,600;1,400" for f in dict.fromkeys([heading, body])]
    return "https://fonts.googleapis.com/css2?" + "&".join(fam) + "&display=swap"


def favicon_svg(letter: str, bg: str, fg: str) -> str:
    letter = escape(letter[:1].upper() or "S")
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' "
        f"fill='{bg}'/><text x='16' y='22' text-anchor='middle' font-family='Georgia,serif' font-size='18' "
        f"font-weight='700' fill='{fg}'>{letter}</text></svg>"
    )


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
) -> dict[str, str]:
    """Return {slug: html}. url_for(slug) builds links, so preview and export can differ."""
    pages_plan = strategy["pages"]
    copy_by_slug = {p["slug"]: p for p in copy["pages"]}
    layout_by_slug = {p["slug"]: p["blocks"] for p in layout["pages"]}
    contact_slug = next((p["slug"] for p in pages_plan if re.search(r"contact|visit|book|order|find", p["slug"])), None)
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
        "url": url_for,
        "fonts_url": fonts_url(t["heading_font"], t["body_font"]),
        "favicon": favicon_svg(business_name, p["accent"], p["accent_ink"]),
        "year": datetime.now(UTC).year,
        "cta_href": url_for(contact_slug) + "#contact" if contact_slug is not None else "#contact",
    }
    template = _env.get_template("page.html.j2")
    out = {}
    for plan in pages_plan:
        page = copy_by_slug.get(plan["slug"])
        if page is None:
            continue
        chosen = layout_by_slug.get(plan["slug"], [])
        blocks = []
        for i, section in enumerate(page["sections"]):
            name = chosen[i] if i < len(chosen) and chosen[i] in LAYOUTS else ("hero_split" if i == 0 else "text")
            blocks.append({"layout": name, "section": section})
        out[plan["slug"]] = template.render(page=page, blocks=blocks, **common)
    return out
