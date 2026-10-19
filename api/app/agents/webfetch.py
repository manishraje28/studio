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

import httpcore
import httpx

MAX_BYTES = 1_500_000
MAX_TEXT = 12_000
MAX_REDIRECTS = 4
TOTAL_DEADLINE = 30  # seconds for all redirect hops and the body together
USER_AGENT = "StudioResearchBot/0.1 (+https://github.com/manishraje28/studio)"


class FetchError(Exception):
    pass


async def _resolve_public(host: str) -> str:
    """Resolve host and return one of its addresses, refusing if ANY address is not public."""
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise FetchError(f"cannot resolve {host}") from exc
    ips = [ipaddress.ip_address(info[4][0]) for info in infos]
    if not ips or any(not ip.is_global or ip.is_multicast for ip in ips):
        raise FetchError(f"{host} resolves to a non-public address")
    return str(ips[0])


async def _assert_public(url: str) -> None:
    """Cheap early check on scheme, port and DNS. The binding check happens in PublicOnlyBackend."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise FetchError("only http and https URLs are allowed")
    if parts.port not in (None, 80, 443):
        raise FetchError("only ports 80 and 443 are allowed")
    if not parts.hostname:
        raise FetchError("URL has no host")
    await _resolve_public(parts.hostname)


class PublicOnlyBackend(httpcore.AsyncNetworkBackend):
    """Resolves and vets the host at connect time, then connects to that exact IP.

    Checking a URL and then letting the HTTP client resolve it again leaves a gap where DNS
    can answer differently (DNS rebinding). Here the address we check is the address we dial.
    TLS still uses the original hostname for SNI and certificate checks, because httpcore
    passes server_hostname separately when it upgrades the stream.
    """

    def __init__(self) -> None:
        self._inner = httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):  # noqa: ASYNC109 (httpcore interface)
        try:
            ip = await _resolve_public(host)
        except FetchError as exc:
            raise httpcore.ConnectError(str(exc)) from exc
        return await self._inner.connect_tcp(
            ip, port, timeout=timeout, local_address=local_address, socket_options=socket_options
        )

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):  # noqa: ASYNC109
        raise httpcore.ConnectError("unix sockets are not allowed")

    async def sleep(self, seconds: float) -> None:
        await self._inner.sleep(seconds)


def public_client() -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport(retries=0)
    # httpx does not expose network_backend, so swap in a pool that uses ours.
    transport._pool = httpcore.AsyncConnectionPool(network_backend=PublicOnlyBackend(), max_connections=10)
    return httpx.AsyncClient(
        transport=transport,
        timeout=15,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
        trust_env=False,
    )


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
    try:
        async with asyncio.timeout(TOTAL_DEADLINE):
            return await _fetch(url, client)
    except TimeoutError as exc:
        raise FetchError(f"page took longer than {TOTAL_DEADLINE}s") from exc


async def _fetch(url: str, client: httpx.AsyncClient | None) -> Page:
    own = client is None
    client = client or public_client()
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
                # We ask for identity encoding; refuse compressed bodies so the size cap
                # counts real bytes, not what a small gzip bomb would inflate to.
                if resp.headers.get("content-encoding", "identity").lower() not in ("identity", ""):
                    raise FetchError("compressed responses are not accepted")
                body = bytearray()
                async for chunk in resp.aiter_bytes():  # identity only, so these are the raw bytes
                    body += chunk
                    if len(body) > MAX_BYTES:
                        break
                parser = _Extractor()
                parser.feed(body.decode(resp.encoding or "utf-8", errors="replace"))
                return parser.result(url)
        raise FetchError("too many redirects")
    except (httpx.HTTPError, httpcore.ConnectError) as exc:
        raise FetchError(f"{type(exc).__name__}: {exc}") from exc
    finally:
        if own:
            await client.aclose()
