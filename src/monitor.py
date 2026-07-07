from __future__ import annotations

import asyncio
import random

from rich.console import Console
from rich.table import Table

from src.captcha_solver import CaptchaSolver
from src.checkout.engine import CheckoutEngine
from src.config import Settings
from src.models import CheckoutResult, ProductStatus, ProductTarget
from src.notifications import Notifier
from src.proxy_manager import ProxyManager
from src.sites.base import SiteAdapter
from src.sites.generic import GenericSiteAdapter
from src.sites.shopify import ShopifySiteAdapter

console = Console()


def get_adapter(
    url: str, settings: Settings, proxy_manager: ProxyManager, captcha_solver: CaptchaSolver
) -> SiteAdapter:
    adapters: list[type[SiteAdapter]] = [ShopifySiteAdapter, GenericSiteAdapter]
    for adapter_cls in adapters:
        adapter = adapter_cls(settings, proxy_manager, captcha_solver)
        if adapter.matches_url(url):
            return adapter
    return GenericSiteAdapter(settings, proxy_manager, captcha_solver)


class ProductMonitor:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._proxy = ProxyManager(settings.proxies)
        self._captcha = CaptchaSolver(settings.captcha)
        self._notifier = Notifier(settings.notifications)
        self._completed: set[str] = set()

    async def run(self) -> None:
        targets = [
            ProductTarget(
                url=p.url,
                size_or_variant=p.size_or_variant,
                max_price=p.max_price,
                quantity=p.quantity,
            )
            for p in self._settings.products
        ]

        if not targets:
            console.print("[red]No products configured. Check config/settings.yaml[/red]")
            return

        self._print_targets(targets)
        await self._notifier.notify_status(f"Monitoring {len(targets)} product(s)...")

        while True:
            tasks = [self._check_product(t) for t in targets if t.url not in self._completed]

            if not tasks:
                console.print("[green]All products checked out successfully![/green]")
                break

            await asyncio.gather(*tasks)

            interval = self._settings.monitor.poll_interval_seconds
            jitter = random.uniform(0, self._settings.monitor.jitter_seconds)
            await asyncio.sleep(interval + jitter)

    async def _check_product(self, target: ProductTarget) -> None:
        adapter = get_adapter(target.url, self._settings, self._proxy, self._captcha)
        console.print(
            f"[dim]Checking [{adapter.name}]: {target.url}[/dim]"
        )

        product = await adapter.check_stock(target)

        if product.status != ProductStatus.IN_STOCK:
            console.print(
                f"[dim]{product.title or target.url}: {product.status.value}[/dim]"
            )
            return

        if target.max_price > 0 and product.price > target.max_price:
            console.print(
                f"[yellow]{product.title}: ${product.price:.2f} exceeds max ${target.max_price:.2f} — skipping[/yellow]"
            )
            return

        console.print(
            f"[bold green]IN STOCK: {product.title or target.url} — ${product.price:.2f}[/bold green]"
        )
        await self._notifier.notify_in_stock(product)

        engine = CheckoutEngine(
            self._settings, adapter, self._proxy, self._captcha, self._notifier
        )
        result = await engine.attempt_checkout(target, product)
        await self._notifier.notify_checkout_result(result)

        if result.result == CheckoutResult.SUCCESS:
            self._completed.add(target.url)
            console.print(
                f"[bold green]CHECKOUT SUCCESS: {product.title}[/bold green]"
            )
        else:
            console.print(
                f"[bold red]CHECKOUT FAILED: {result.result.value} — {result.message}[/bold red]"
            )

    def _print_targets(self, targets: list[ProductTarget]) -> None:
        table = Table(title="Monitoring Targets")
        table.add_column("URL", style="cyan", max_width=60)
        table.add_column("Variant", style="green")
        table.add_column("Max Price", style="yellow")
        table.add_column("Qty", style="magenta")

        for t in targets:
            table.add_row(
                t.url,
                t.size_or_variant or "—",
                f"${t.max_price:.2f}" if t.max_price else "—",
                str(t.quantity),
            )
        console.print(table)
