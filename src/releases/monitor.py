from __future__ import annotations

import asyncio
import random

from rich.console import Console
from rich.table import Table

from src.config import Settings
from src.notifications import Notifier
from src.proxy_manager import ProxyManager
from src.releases.models import ProductRelease
from src.releases.onepiece_scraper import OnePieceScraper
from src.releases.pokemon_scraper import PokemonScraper
from src.releases.tracker import ReleaseTracker

console = Console()


class ReleaseMonitor:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._proxy = ProxyManager(settings.proxies)
        self._notifier = Notifier(settings.notifications)
        self._tracker = ReleaseTracker()
        self._scrapers = self._build_scrapers()

    def _build_scrapers(self) -> list:
        scrapers = []
        games = self._settings.releases.games

        if "pokemon" in games:
            scrapers.append(PokemonScraper())
        if "one_piece" in games:
            scrapers.append(OnePieceScraper())

        return scrapers

    async def run(self) -> None:
        if not self._scrapers:
            console.print("[red]No games configured for release monitoring.[/red]")
            return

        game_names = [s.game.value for s in self._scrapers]
        console.print(f"[cyan]Monitoring releases for: {', '.join(game_names)}[/cyan]")
        await self._notifier.notify_status(
            f"Release monitor started — watching {', '.join(game_names)}"
        )

        first_run = True
        while True:
            await self._check_all(first_run=first_run)
            first_run = False

            interval = self._settings.releases.poll_interval_seconds
            jitter = random.uniform(0, min(interval * 0.2, 30))
            next_check = interval + jitter
            console.print(f"[dim]Next release check in {next_check:.0f}s[/dim]")
            await asyncio.sleep(next_check)

    async def check_once(self) -> list[ProductRelease]:
        return await self._check_all(first_run=True)

    async def _check_all(self, first_run: bool = False) -> list[ProductRelease]:
        all_new: list[ProductRelease] = []
        proxy = self._proxy.get_httpx_proxy()

        for scraper in self._scrapers:
            try:
                console.print(f"[dim]Fetching {scraper.game.value} releases...[/dim]")
                releases = await scraper.fetch_releases(proxy)

                new_releases = self._tracker.filter_new(releases)

                if first_run and new_releases:
                    console.print(
                        f"[cyan]First run: cataloging {len(releases)} known "
                        f"{scraper.game.value} releases[/cyan]"
                    )
                    if not self._settings.releases.notify_on_first_run:
                        for r in releases:
                            self._tracker.mark_seen(r)
                        continue

                if new_releases:
                    self._print_new_releases(new_releases)
                    for release in new_releases:
                        await self._notifier.notify_new_release(release)
                        self._tracker.mark_seen(release)
                    all_new.extend(new_releases)
                else:
                    console.print(
                        f"[dim]{scraper.game.value}: no new releases[/dim]"
                    )

            except Exception as e:
                console.print(f"[red]Error checking {scraper.game.value}: {e}[/red]")
                await self._notifier.notify_error(
                    f"Release check failed for {scraper.game.value}: {e}"
                )

        return all_new

    def _print_new_releases(self, releases: list[ProductRelease]) -> None:
        table = Table(title="New Releases Found!")
        table.add_column("Game", style="magenta")
        table.add_column("Title", style="cyan", max_width=50)
        table.add_column("Type", style="green")
        table.add_column("Release Date", style="yellow")
        table.add_column("Price", style="white")

        for r in releases:
            table.add_row(
                r.game.value,
                r.title,
                r.product_type or "—",
                r.release_date or "—",
                r.price or "—",
            )
        console.print(table)
