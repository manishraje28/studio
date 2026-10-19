"""Publish a static site to Cloudflare Pages through its Direct Upload API.

Flow: ensure the project exists -> get an upload JWT -> ask which files are missing ->
upload those (base64, batched) -> upsert hashes -> create a deployment with a manifest.
"""

import base64
import hashlib
import json
import mimetypes
import re

import httpx

API = "https://api.cloudflare.com/client/v4"


class PublishError(Exception):
    pass


def project_name(business_name: str, project_id: str) -> str:
    """Cloudflare project names: lowercase letters, digits and dashes, at most 58 characters."""
    base = re.sub(r"[^a-z0-9]+", "-", business_name.lower()).strip("-")[:40] or "site"
    return f"{base}-{project_id.replace('-', '')[:6]}"


def file_hash(path: str, data: bytes) -> str:
    ext = path.rsplit(".", 1)[-1] if "." in path else ""
    return hashlib.sha256(base64.b64encode(data) + ext.encode()).hexdigest()[:32]


def _ok(r: httpx.Response, what: str) -> dict:
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400 or not body.get("success", True):
        errors = "; ".join(e.get("message", "") for e in body.get("errors", [])) or r.text[:200]
        raise PublishError(f"{what} failed ({r.status_code}): {errors}")
    return body.get("result") or {}


async def deploy(files: dict[str, bytes], name: str, account_id: str, token: str) -> dict:
    """Upload files and create a production deployment. Returns {"url", "project_url", "id"}."""
    auth = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.get(f"{API}/accounts/{account_id}/pages/projects/{name}", headers=auth)
        if r.status_code == 404:
            _ok(
                await c.post(
                    f"{API}/accounts/{account_id}/pages/projects",
                    headers=auth,
                    json={"name": name, "production_branch": "main"},
                ),
                "Creating the site",
            )
            r = await c.get(f"{API}/accounts/{account_id}/pages/projects/{name}", headers=auth)
        project = _ok(r, "Reading the site")

        jwt = _ok(
            await c.get(f"{API}/accounts/{account_id}/pages/projects/{name}/upload-token", headers=auth),
            "Getting an upload token",
        )["jwt"]
        up = {"Authorization": f"Bearer {jwt}"}

        hashes = {path: file_hash(path, data) for path, data in files.items()}
        missing = set(
            _ok(
                await c.post(f"{API}/pages/assets/check-missing", headers=up, json={"hashes": list(hashes.values())}),
                "Checking files",
            )
        )
        batch, size = [], 0
        for path, data in files.items():
            h = hashes[path]
            if h not in missing:
                continue
            item = {
                "key": h,
                "value": base64.b64encode(data).decode(),
                "metadata": {"contentType": mimetypes.guess_type(path)[0] or "application/octet-stream"},
                "base64": True,
            }
            batch.append(item)
            size += len(item["value"])
            if size > 20_000_000:
                _ok(await c.post(f"{API}/pages/assets/upload", headers=up, json=batch), "Uploading files")
                batch, size = [], 0
        if batch:
            _ok(await c.post(f"{API}/pages/assets/upload", headers=up, json=batch), "Uploading files")
        _ok(
            await c.post(f"{API}/pages/assets/upsert-hashes", headers=up, json={"hashes": list(hashes.values())}),
            "Saving files",
        )

        manifest = {f"/{path}": h for path, h in hashes.items()}
        dep = _ok(
            await c.post(
                f"{API}/accounts/{account_id}/pages/projects/{name}/deployments",
                headers=auth,
                files={"manifest": (None, json.dumps(manifest)), "branch": (None, "main")},
            ),
            "Publishing",
        )
    subdomain = project.get("subdomain") or f"{name}.pages.dev"
    return {"url": f"https://{subdomain}", "deployment_url": dep.get("url"), "id": dep.get("id")}
