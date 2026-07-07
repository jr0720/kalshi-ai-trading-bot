from __future__ import annotations

import re

from rich.console import Console

from src.releases.base_scraper import ReleaseScraper
from src.releases.models import CardGame, ProductRelease

console = Console()

POKEMON_PRODUCTS_URL = "https://www.pokemon.com/us/pokemon-tcg/pokemon-cards/series"
POKEMON_BASE = "https://www.pokemon.com"


class PokemonScraper(ReleaseScraper):
    game = CardGame.POKEMON

    async def fetch_releases(
        self, proxy: dict[str, str] | None = None
    ) -> list[ProductRelease]:
        releases: list[ProductRelease] = []

        try:
            releases.extend(await self._scrape_series_page(proxy))
        except Exception as e:
            console.print(f"[red]Pokemon series scrape failed: {e}[/red]")

        try:
            releases.extend(await self._scrape_pokemon_center(proxy))
        except Exception as e:
            console.print(f"[red]Pokemon Center scrape failed: {e}[/red]")

        return releases

    async def _scrape_series_page(
        self, proxy: dict[str, str] | None
    ) -> list[ProductRelease]:
        html = await self._fetch(POKEMON_PRODUCTS_URL, proxy)
        releases = []

        blocks = re.findall(
            r'<li[^>]*class="[^"]*series-list[^"]*"[^>]*>(.*?)</li>',
            html,
            re.DOTALL,
        )

        for block in blocks:
            link_match = re.search(r'href="([^"]+)"', block)
            title_match = re.search(r'<h3[^>]*>(.*?)</h3>', block, re.DOTALL)
            if not title_match:
                title_match = re.search(r'alt="([^"]+)"', block)

            img_match = re.search(r'<img[^>]+src="([^"]+)"', block)

            if link_match and title_match:
                url = link_match.group(1)
                if not url.startswith("http"):
                    url = POKEMON_BASE + url

                title = self._clean_text(title_match.group(1))
                image_url = img_match.group(1) if img_match else ""

                releases.append(ProductRelease(
                    game=CardGame.POKEMON,
                    title=title,
                    url=url,
                    image_url=image_url,
                    product_type="expansion",
                ))

        if not blocks:
            link_pattern = re.findall(
                r'<a[^>]+href="(/us/pokemon-tcg/pokemon-cards/[^"]+)"[^>]*>.*?'
                r'(?:<img[^>]+alt="([^"]*)"[^>]*/?>|<h\d[^>]*>([^<]+)</h\d>)',
                html,
                re.DOTALL,
            )
            for href, alt_title, h_title in link_pattern:
                title = self._clean_text(alt_title or h_title)
                if not title:
                    continue
                url = POKEMON_BASE + href if not href.startswith("http") else href
                releases.append(ProductRelease(
                    game=CardGame.POKEMON,
                    title=title,
                    url=url,
                    product_type="expansion",
                ))

        console.print(f"[dim]Pokemon series page: found {len(releases)} entries[/dim]")
        return releases

    async def _scrape_pokemon_center(
        self, proxy: dict[str, str] | None
    ) -> list[ProductRelease]:
        url = "https://www.pokemoncenter.com/category/trading-card-game"
        html = await self._fetch(url, proxy)
        releases = []

        product_blocks = re.findall(
            r'<a[^>]+href="(/product/[^"]+)"[^>]*>(.*?)</a>',
            html,
            re.DOTALL,
        )

        for href, block in product_blocks:
            title_match = re.search(r'<(?:h[23456]|span|p)[^>]*>(.*?)</(?:h[23456]|span|p)>', block, re.DOTALL)
            img_match = re.search(r'<img[^>]+src="([^"]+)"', block)
            price_match = re.search(r'\$(\d+\.\d{2})', block)

            title = self._clean_text(title_match.group(1)) if title_match else ""
            if not title or len(title) < 3:
                continue

            tcg_keywords = ["booster", "elite trainer", "collection", "box", "pack", "tin", "etb", "bundle"]
            if not any(kw in title.lower() for kw in tcg_keywords):
                continue

            full_url = "https://www.pokemoncenter.com" + href

            releases.append(ProductRelease(
                game=CardGame.POKEMON,
                title=title,
                url=full_url,
                price=f"${price_match.group(1)}" if price_match else "",
                image_url=img_match.group(1) if img_match else "",
                product_type="product",
            ))

        console.print(f"[dim]Pokemon Center: found {len(releases)} TCG products[/dim]")
        return releases
