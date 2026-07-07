from __future__ import annotations

import re

from rich.console import Console

from src.releases.base_scraper import ReleaseScraper
from src.releases.models import CardGame, ProductRelease

console = Console()

ONEPIECE_PRODUCTS_URL = "https://en.onepiece-cardgame.com/products/"
ONEPIECE_BASE = "https://en.onepiece-cardgame.com"


class OnePieceScraper(ReleaseScraper):
    game = CardGame.ONE_PIECE

    async def fetch_releases(
        self, proxy: dict[str, str] | None = None
    ) -> list[ProductRelease]:
        releases: list[ProductRelease] = []

        try:
            releases.extend(await self._scrape_products_page(proxy))
        except Exception as e:
            console.print(f"[red]One Piece products scrape failed: {e}[/red]")

        try:
            releases.extend(await self._scrape_product_lineup(proxy))
        except Exception as e:
            console.print(f"[red]One Piece lineup scrape failed: {e}[/red]")

        return releases

    async def _scrape_products_page(
        self, proxy: dict[str, str] | None
    ) -> list[ProductRelease]:
        html = await self._fetch(ONEPIECE_PRODUCTS_URL, proxy)
        releases = []

        product_blocks = re.findall(
            r'<a[^>]+href="([^"]*products?[^"]*)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL | re.IGNORECASE,
        )

        for href, block in product_blocks:
            title_match = re.search(
                r'<(?:h[23456]|span|p|div)[^>]*class="[^"]*(?:title|name|heading)[^"]*"[^>]*>(.*?)</(?:h[23456]|span|p|div)>',
                block,
                re.DOTALL,
            )
            if not title_match:
                title_match = re.search(r'<(?:h[23456]|span|p)[^>]*>(.*?)</(?:h[23456]|span|p)>', block, re.DOTALL)

            img_match = re.search(r'<img[^>]+src="([^"]+)"', block)
            alt_match = re.search(r'alt="([^"]+)"', block)

            title = ""
            if title_match:
                title = self._clean_text(title_match.group(1))
            elif alt_match:
                title = self._clean_text(alt_match.group(1))

            if not title or len(title) < 3:
                continue

            url = href
            if not url.startswith("http"):
                url = ONEPIECE_BASE + ("" if url.startswith("/") else "/") + url

            date_match = re.search(
                r'(?:release|available|on sale)[:\s]*(\w+\s+\d{1,2},?\s*\d{4}|\d{1,2}/\d{1,2}/\d{4})',
                block,
                re.IGNORECASE,
            )

            releases.append(ProductRelease(
                game=CardGame.ONE_PIECE,
                title=title,
                url=url,
                release_date=date_match.group(1) if date_match else "",
                image_url=img_match.group(1) if img_match else "",
                product_type="product",
            ))

        console.print(f"[dim]One Piece products page: found {len(releases)} entries[/dim]")
        return releases

    async def _scrape_product_lineup(
        self, proxy: dict[str, str] | None
    ) -> list[ProductRelease]:
        lineup_urls = [
            "https://en.onepiece-cardgame.com/products/booster-pack/",
            "https://en.onepiece-cardgame.com/products/starter-deck/",
            "https://en.onepiece-cardgame.com/products/other/",
        ]

        releases = []
        for lineup_url in lineup_urls:
            try:
                html = await self._fetch(lineup_url, proxy)
                releases.extend(self._parse_lineup_page(html, lineup_url))
            except Exception as e:
                console.print(f"[dim]One Piece lineup {lineup_url} skipped: {e}[/dim]")

        console.print(f"[dim]One Piece lineup pages: found {len(releases)} entries[/dim]")
        return releases

    def _parse_lineup_page(self, html: str, page_url: str) -> list[ProductRelease]:
        releases = []

        link_blocks = re.findall(
            r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )

        for href, block in link_blocks:
            if "/products/" not in href:
                continue

            img_match = re.search(r'<img[^>]+src="([^"]+)"', block)
            alt_match = re.search(r'alt="([^"]+)"', block)
            title_match = re.search(r'<(?:h[23456]|span|p)[^>]*>(.*?)</(?:h[23456]|span|p)>', block, re.DOTALL)

            title = ""
            if title_match:
                title = self._clean_text(title_match.group(1))
            elif alt_match:
                title = self._clean_text(alt_match.group(1))

            if not title or len(title) < 3:
                continue

            url = href
            if not url.startswith("http"):
                url = ONEPIECE_BASE + ("" if url.startswith("/") else "/") + url

            riftbound_keywords = ["riftbound", "op-", "booster", "starter", "deck", "box"]
            if not any(kw in title.lower() for kw in riftbound_keywords):
                continue

            releases.append(ProductRelease(
                game=CardGame.ONE_PIECE,
                title=title,
                url=url,
                image_url=img_match.group(1) if img_match else "",
                product_type="lineup",
            ))

        return releases
