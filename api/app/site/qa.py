"""Checks that run on the rendered pages. Pure code, no browser, so they are fast and free.

Each check returns findings with a severity. "fail" blocks nothing on its own yet, but is shown
to the owner and counted in the score; the critic agent adds a judgement on the copy.
"""

import re
from dataclasses import asdict, dataclass
from html.parser import HTMLParser

MAX_PAGE_KB = 120


@dataclass
class Finding:
    page: str
    check: str
    severity: str  # "fail" | "warn" | "pass"
    message: str


class _Scan(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.headings: list[tuple[int, str]] = []
        self.links: list[str] = []
        self.title = ""
        self.description = ""
        self.lang = ""
        self.viewport = False
        self.placeholders = 0
        self.scripts = 0
        self._in: str | None = None
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang") or ""
        if tag == "meta" and a.get("name") == "viewport":
            self.viewport = True
        if tag == "meta" and a.get("name") == "description":
            self.description = a.get("content") or ""
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "script":
            self.scripts += 1
        if tag == "span" and a.get("class") == "ph":
            self.placeholders += 1
        if tag == "title" or re.fullmatch(r"h[1-6]", tag):
            self._in, self._buf = tag, ""

    def handle_endtag(self, tag):
        if tag == self._in:
            text = " ".join(self._buf.split())
            if tag == "title":
                self.title = text
            else:
                self.headings.append((int(tag[1]), text))
            self._in = None

    def handle_data(self, data):
        if self._in:
            self._buf += data


def check_site(pages: dict[str, str], link_for) -> list[Finding]:
    """pages: {slug: html}. link_for(slug) is how pages link to each other (without query string)."""
    out: list[Finding] = []
    known = {link_for(slug) for slug in pages}
    for slug, html in pages.items():
        name = slug or "home"
        s = _Scan()
        s.feed(html)
        add = lambda check, sev, msg, n=name: out.append(Finding(n, check, sev, msg))  # noqa: E731

        h1 = [t for lvl, t in s.headings if lvl == 1]
        add("one h1", "pass" if len(h1) == 1 else "fail", f"{len(h1)} main headings" if len(h1) != 1 else h1[0])
        jumps = [(a, b) for (a, _), (b, _) in zip(s.headings, s.headings[1:], strict=False) if b > a + 1]
        add("heading order", "warn" if jumps else "pass", "skips a heading level" if jumps else "headings in order")
        add("title length", "pass" if 10 <= len(s.title) <= 60 else "warn", f"{len(s.title)} characters")
        add(
            "meta description",
            "pass" if 50 <= len(s.description) <= 160 else "warn",
            f"{len(s.description)} characters",
        )
        add("mobile ready", "pass" if s.viewport and s.lang else "fail", "viewport and language set")
        add("no scripts", "pass" if s.scripts == 0 else "fail", f"{s.scripts} script tags")

        internal = [
            h.split("?")[0].split("#")[0] for h in s.links if not h.startswith(("http", "mailto:", "tel:", "#"))
        ]
        broken = sorted({h for h in internal if h and h not in known})
        add("internal links", "fail" if broken else "pass", f"broken: {', '.join(broken)}" if broken else "all resolve")

        kb = len(html.encode()) / 1024
        add("page weight", "pass" if kb <= MAX_PAGE_KB else "warn", f"{kb:.0f} KB")
        if s.placeholders:
            add("details needed", "warn", f"{s.placeholders} [placeholders] still need your input")

        text = re.sub(r"<[^>]+>", " ", html)
        if re.search(r"\b(lorem ipsum|todo|tbd)\b", text, re.I):
            add("leftover text", "fail", "contains filler text")
    return out


def score(findings: list[Finding]) -> int:
    """100 minus 15 per failure and 4 per warning, floored at 0. Placeholders do not count against it."""
    penalty = sum(
        15 if f.severity == "fail" else 4 for f in findings if f.severity != "pass" and f.check != "details needed"
    )
    return max(0, 100 - penalty)


def as_dicts(findings: list[Finding]) -> list[dict]:
    return [asdict(f) for f in findings]
