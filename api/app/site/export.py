"""Turn a project into a self-contained static site: HTML pages, photos, a README.

Used by both "Download site" (ZIP) and "Publish" (Cloudflare Pages). Photos are copied in,
so the published site does not depend on Studio's servers or on stock-photo hotlinks.
"""

import asyncio
import hashlib
import io
import zipfile
from dataclasses import dataclass

import httpx

from app.agents.webfetch import public_client
from app.site.images import upload_path

MAX_PHOTO_BYTES = 6 * 1024 * 1024


@dataclass
class StaticSite:
    files: dict[str, bytes]  # path like "index.html" or "services/index.html" -> content


def page_path(slug: str) -> str:
    return "index.html" if not slug else f"{slug}/index.html"


def page_url(slug: str) -> str:
    return "/" if not slug else f"/{slug}/"


async def _fetch_photo(client: httpx.AsyncClient, url: str) -> bytes | None:
    try:
        async with client.stream("GET", url, follow_redirects=True) as r:
            if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image/"):
                return None
            data = bytearray()
            async for chunk in r.aiter_bytes():
                data += chunk
                if len(data) > MAX_PHOTO_BYTES:
                    return None
            return bytes(data)
    except httpx.HTTPError:
        return None


async def collect_photos(project_id, pool: list[dict]) -> tuple[list[dict], dict[str, bytes]]:
    """Copy every photo into assets/. Owner photos come from disk; stock photos are downloaded
    through the SSRF-safe client. Photos that cannot be fetched are dropped from the pool."""
    files: dict[str, bytes] = {}
    out: list[dict] = []
    stock = [p for p in pool if p.get("url", "").startswith("https://")]
    async with public_client() as client:
        fetched = await asyncio.gather(*(_fetch_photo(client, p["url"]) for p in stock))
    by_url = {p["url"]: data for p, data in zip(stock, fetched, strict=True)}
    for p in pool:
        if p.get("url", "").startswith("https://"):
            data = by_url.get(p["url"])
        else:
            path = upload_path(project_id, p.get("name") or p.get("url", "").split("/")[-1].split("?")[0])
            data = path.read_bytes() if path else None
        if not data:
            continue
        name = f"assets/{hashlib.sha256(data).hexdigest()[:16]}.jpg"
        files[name] = data
        out.append({**p, "url": f"/{name}"})
    return out, files


README = """# {name}

This folder is your complete website, made with Studio.

- Every page is a plain HTML file. Open index.html in a browser to look around
  (links work best once the site is hosted, because they start with "/").
- Photos are in assets/. Credits for free stock photos are listed in each page's footer.
- To host it for free, drag this folder into Cloudflare Pages, Netlify or GitHub Pages.

The code is yours to keep, change and host anywhere.
"""


def to_zip(site: StaticSite, business_name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, data in sorted(site.files.items()):
            z.writestr(path, data)
        z.writestr("README.md", README.format(name=business_name))
    return buf.getvalue()
