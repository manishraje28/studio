"""Check your provider keys: `uv run python -m app.llm.smoke "Say hello in five words"`."""

import asyncio
import sys

from pydantic import BaseModel

from app.llm import get_llm
from app.migrate import migrate


class Tagline(BaseModel):
    tagline: str
    why: str


async def main(prompt: str) -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    await migrate()
    llm = get_llm()
    print("chain:", [f"{p.name}:{p.model}" for p in llm.providers] or "none configured")
    out = await llm.complete([{"role": "user", "content": prompt}], agent="smoke")
    print(f"[{out.provider}/{out.model}] {out.text.strip()}")
    tag = await llm.complete_json(
        Tagline, [{"role": "user", "content": "Write a tagline for a small café in Pune called Kaapi House."}]
    )
    print("json ok:", tag.model_dump())


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or "Say hello in five words."))
