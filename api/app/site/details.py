"""Owner-supplied details that fill the copy's [placeholders].

The copy artifact keeps the placeholders; values are applied at render time, so the owner
can change a phone number later without rewriting any copy.
"""

import re

PLACEHOLDER = re.compile(r"\[([^\[\]]{1,80})\]")
# Photos and embeds cannot be typed into a form; older copy may still ask for them, so they are dropped.
MEDIA = re.compile(r"photo|image|picture|thumbnail|gallery|video|map embed|embed|logo|insert", re.IGNORECASE)


def is_media(label: str) -> bool:
    return bool(MEDIA.search(label))


def find_placeholders(copy: dict) -> list[str]:
    """Unique placeholder labels in page order, e.g. ["phone number", "opening hours"]."""
    seen: dict[str, None] = {}
    for page in copy.get("pages", []):
        texts = [page.get("seo_title", ""), page.get("meta_description", "")]
        for s in page.get("sections", []):
            texts += [s.get("heading", ""), s.get("body", ""), s.get("cta_label") or ""]
        for t in texts:
            for m in PLACEHOLDER.finditer(t):
                if not is_media(m.group(1)):
                    seen.setdefault(m.group(1).strip(), None)
    return list(seen)


def fill(copy: dict, values: dict[str, str]) -> dict:
    """Return a copy of the copy artifact with known placeholders replaced. Unknown ones stay."""
    lookup = {k.strip().lower(): v.strip() for k, v in values.items() if v and v.strip()}

    def sub(text: str | None) -> str | None:
        if not text:
            return text

        def repl(m: re.Match) -> str:
            label = m.group(1).strip()
            return "" if is_media(label) else lookup.get(label.lower(), m.group(0))

        return re.sub(r"[ 	]{2,}", " ", PLACEHOLDER.sub(repl, text)).strip()

    pages = []
    for page in copy.get("pages", []):
        sections = [
            {**s, "heading": sub(s.get("heading")), "body": sub(s.get("body")), "cta_label": sub(s.get("cta_label"))}
            for s in page.get("sections", [])
        ]
        pages.append(
            {
                **page,
                "seo_title": sub(page.get("seo_title")),
                "meta_description": sub(page.get("meta_description")),
                "sections": sections,
            }
        )
    return {**copy, "pages": pages}
