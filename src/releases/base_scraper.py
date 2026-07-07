from __future__ import annotations

import abc
import re

import httpx
from rich.console import Console

from src.releases.models import CardGame, ProductRelease

console = Console()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class ReleaseScraper(abc.ABC):
    game: CardGame

    async def _fetch(self, url: str, proxy: dict[str, str] | None = None) -> str:
        async with httpx.AsyncClient(
            headers=HEADERS,
            proxies=proxy,
            timeout=20,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    @abc.abstractmethod
    async def fetch_releases(
        self, proxy: dict[str, str] | None = None
    ) -> list[ProductRelease]:
        ...

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
