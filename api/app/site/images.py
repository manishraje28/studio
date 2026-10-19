"""Photos for client sites.

Owner uploads always come first. When there are not enough, we search Openverse: a free,
keyless index of Creative Commons photos (Flickr, Wikimedia and others). Only licences that
allow commercial use, only photographs, and every stock photo carries its credit line.
"""

import asyncio
import io
import re
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

OPENVERSE = "https://api.openverse.org/v1/images/"
USER_AGENT = "StudioBot/0.1 (+https://github.com/manishraje28/studio)"
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_PHOTOS = 12
MAX_EDGE = 1800
# Refuse decompression bombs before decoding (Pillow raises above this many pixels).
Image.MAX_IMAGE_PIXELS = 40_000_000


@dataclass
class Photo:
    url: str
    alt: str
    credit: str | None = None  # None for the owner's own photos
    source: str = "owner"
    width: int = 0
    height: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


COMMONS = "https://commons.wikimedia.org/w/api.php"
# Professional CC0 libraries indexed by Openverse; searched first.
PREMIUM_SOURCES = "stocksnap,wordpress,rawpixel"
# Skip people (the design rules ban stock people) and non-photos.
REJECT = re.compile(
    r"\b(people|person|man|men|woman|women|girl|boy|bride|groom|model|portrait|face|selfie|child|kid|crowd|"
    r"png|sticker|silhouette|illustration|vector|clipart|icon|logo|drawing|cartoon|mockup|template)\b",
    re.IGNORECASE,
)
OK_LICENSES = ("cc0", "cc by", "cc-by", "public domain", "pd")


def _usable(w: int, h: int) -> bool:
    return w >= 900 and h > 0 and 1.1 <= w / h <= 2.2


async def _openverse(client: httpx.AsyncClient, q: str, sources: str | None = None) -> list[Photo]:
    params = {"q": q, "license_type": "commercial", "page_size": 20}
    if sources:
        params["source"] = sources
    try:
        r = await client.get(OPENVERSE, params=params, timeout=50)
        r.raise_for_status()
        results = r.json().get("results", [])
    except (httpx.HTTPError, ValueError):
        return []
    out = []
    for item in results:
        w, h, url = item.get("width") or 0, item.get("height") or 0, item.get("url") or ""
        words = " ".join([item.get("title") or ""] + [t.get("name", "") for t in item.get("tags") or []])
        if item.get("mature") or not url.startswith("https://") or not _usable(w, h) or REJECT.search(words):
            continue
        credit = item.get("attribution") or f"{item.get('creator') or 'Unknown'}, {item.get('license')}"
        out.append(Photo(url, (item.get("title") or q)[:120], credit, "openverse", w, h))
    return out


def _plain(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html or "").strip()


async def _commons(client: httpx.AsyncClient, q: str) -> list[Photo]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrlimit": 12,
        "gsrsearch": f"filetype:bitmap {q}",
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1600,
    }
    try:
        r = await client.get(COMMONS, params=params, timeout=20)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages", {}).values()
    except (httpx.HTTPError, ValueError):
        return []
    out = []
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic = _plain(meta.get("LicenseShortName", {}).get("value", ""))
        url = info.get("thumburl") or ""
        w, h = info.get("thumbwidth") or 0, info.get("thumbheight") or 0
        title = page.get("title", "").removeprefix("File:").rsplit(".", 1)[0]
        if (
            not url.startswith("https://")
            or not lic.lower().startswith(OK_LICENSES)
            or not _usable(w, h)
            or REJECT.search(title)
            or re.search(r"\b1[89]\d\d\b", title)  # archive photos read as dated
        ):
            continue
        artist = _plain(meta.get("Artist", {}).get("value", "")) or "Unknown"
        out.append(
            Photo(url, title[:120], f'"{title[:80]}" by {artist[:80]}, {lic}, via Wikimedia Commons', "commons", w, h)
        )
    return out


async def search_stock(queries: list[str], per_query: int = 3, client: httpx.AsyncClient | None = None) -> list[Photo]:
    """Credited CC photos for each query from Openverse and Wikimedia Commons, searched in parallel."""
    own = client is None
    client = client or httpx.AsyncClient(headers={"User-Agent": USER_AGENT})
    try:
        # Premium CC0 libraries first, Wikimedia Commons to fill gaps. General Flickr results were too often
        # off topic, and fewer Openverse calls keep us inside its anonymous rate limit.
        premium, commons = await asyncio.gather(
            asyncio.gather(*(_openverse(client, q, PREMIUM_SOURCES) for q in queries)),
            asyncio.gather(*(_commons(client, q) for q in queries)),
        )
    finally:
        if own:
            await client.aclose()
    out: list[Photo] = []
    seen: set[str] = set()
    for i in range(len(queries)):
        taken = 0
        words = {w for w in queries[i].lower().split() if len(w) > 3}
        relevant = [p for p in commons[i] if words & set(re.findall(r"[a-z]+", p.alt.lower()))]
        candidates = premium[i] + relevant
        for photo in candidates:
            if photo.url in seen:
                continue
            seen.add(photo.url)
            out.append(photo)
            taken += 1
            if taken >= per_query:
                break
    return out


class UploadError(ValueError):
    pass


def save_upload(project_id: uuid.UUID, data: bytes) -> tuple[str, int, int]:
    """Validate an image, fix rotation, strip metadata, cap its size, store as JPEG. Returns (name, w, h)."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise UploadError("Photos must be under 8 MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()  # catches truncated or fake files
        img = Image.open(io.BytesIO(data))
    except Image.DecompressionBombError as exc:
        raise UploadError("That photo is too large") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise UploadError("That file is not a photo we can read (use JPG, PNG or WebP)") from exc
    if img.format not in ("JPEG", "PNG", "WEBP"):
        raise UploadError("Use JPG, PNG or WebP")
    # Header-only size check before decoding: Pillow's own bomb error only fires at twice MAX_IMAGE_PIXELS.
    if img.width * img.height > Image.MAX_IMAGE_PIXELS:
        raise UploadError("That photo is too large")
    if img.format == "JPEG":
        img.draft("RGB", (MAX_EDGE, MAX_EDGE))  # decode JPEGs at reduced size: much less memory and CPU
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE))
    folder = UPLOAD_ROOT / str(project_id)
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(folder / name, "JPEG", quality=84, optimize=True, progressive=True)  # no EXIF: location data dropped
    return name, img.width, img.height


def upload_path(project_id: uuid.UUID, name: str) -> Path | None:
    """Resolve a stored photo, refusing anything that is not a plain file name we created."""
    if not name.endswith(".jpg") or len(name) != 36 or not all(c in "0123456789abcdef" for c in name[:32]):
        return None
    path = UPLOAD_ROOT / str(project_id) / name
    return path if path.is_file() else None


def delete_upload(project_id: uuid.UUID, name: str) -> None:
    if path := upload_path(project_id, name):
        path.unlink(missing_ok=True)
