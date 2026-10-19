"""Fetch a public web page and reduce it to readable text for the agents.

The URL comes from the client's brief, so it is untrusted:
- only http(s) on ports 80/443
- every hop (including redirects) must resolve to public IP addresses only
- size and time limits
The page text is later handed to a model as data, never as instructions.
"""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

MAX_BYTES = 1_500_000
MAX_TEXT = 12_000
MAX_REDIRECTS = 4
USER_AGENT = "StudioResearchBot/0.1 (+https://github.com/manishraje28/studio)"


class FetchError(Exception):
    pass


async def _assert_public(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FetchError("only http and https URLs are allowed")
    if parts.port not in (None, 80, 443):
        raise FetchError("only ports 80 and 443 are allowed")
    host = parts.hostname
    if not host:
        raise FetchError("URL has no host")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError(f"cannot resolve {host}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise FetchError(f"{host} resolves to a non-public address")


@dataclass
class Page:
    url: str
    title: str = ""
    description: str = ""
    headings: list[str] = field(default_factory=list)
    text: str = ""


class _Extractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "iframe"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.page = Page(url="")
        self._skip = 0
        self._tag: str | None = None
        self._chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        self._tag = tag
        if tag == "meta":
            a = dict(attrs)
            if (a.get("name") or a.get("property") or "").lower() in ("description", "og:description"):
                self.page.description = self.page.description or (a.get("content") or "").strip()

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        self._tag = None

    def handle_data(self, data):
        if self._skip:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._tag == "title":
            self.page.title = self.page.title or text
        elif self._tag in ("h1", "h2", "h3") and len(self.page.headings) < 40:
            self.page.headings.append(text)
        self._chunks.append(text)

    def result(self, url: str) -> Page:
        self.page.url = url
        self.page.text = " ".join(self._chunks)[:MAX_TEXT]
        return self.page


async def fetch_page(url: str, client: httpx.AsyncClient | None = None) -> Page:
    own = client is None
    client = client or httpx.AsyncClient(timeout=15, headers={"User-Agent": USER_AGENT})
    try:
        for _ in range(MAX_REDIRECTS + 1):
            await _assert_public(url)
            async with client.stream("GET", url, follow_redirects=False) as resp:
                if resp.is_redirect:
                    url = urljoin(url, resp.headers.get("location", ""))
                    continue
                if resp.status_code != 200:
                    raise FetchError(f"HTTP {resp.status_code}")
                ctype = resp.headers.get("content-type", "")
                if "html" not in ctype and "text" not in ctype:
                    raise FetchError(f"not a web page ({ctype or 'unknown type'})")
                body = bytearray()
                async for chunk in resp.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        break
                parser = _Extractor()
                parser.feed(body.decode(resp.encoding or "utf-8", errors="replace"))
                return parser.result(url)
        raise FetchError("too many redirects")
    except httpx.HTTPError as exc:
        raise FetchError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        if own:
            await client.aclose()
