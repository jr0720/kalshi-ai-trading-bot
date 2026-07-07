from __future__ import annotations

import httpx
from rich.console import Console

from src.config import NotificationsConfig
from src.models import CheckoutAttempt, CheckoutResult, ProductInfo
from src.releases.models import ProductRelease

console = Console()


class Notifier:
    def __init__(self, config: NotificationsConfig):
        self._config = config

    async def notify_in_stock(self, product: ProductInfo) -> None:
        msg = f"IN STOCK: {product.title or product.url} — ${product.price:.2f}"
        await self._send(msg, color=0x00FF00)

    async def notify_checkout_result(self, attempt: CheckoutAttempt) -> None:
        if attempt.result == CheckoutResult.SUCCESS:
            msg = f"CHECKOUT SUCCESS: {attempt.product.title or attempt.product.url}"
            if attempt.order_number:
                msg += f" — Order #{attempt.order_number}"
            color = 0x00FF00
        else:
            msg = (
                f"CHECKOUT FAILED: {attempt.product.title or attempt.product.url}"
                f" — {attempt.result.value}: {attempt.message}"
            )
            color = 0xFF0000

        await self._send(msg, color=color)

    async def notify_new_release(self, release: ProductRelease) -> None:
        game_label = release.game.value.replace("_", " ").title()
        msg = f"NEW RELEASE: [{game_label}] {release.title}"
        if release.release_date:
            msg += f" — {release.release_date}"
        if release.price:
            msg += f" — {release.price}"

        if self._config.console.get("enabled", True):
            console.print(f"[bold magenta]{msg}[/bold magenta]")
            if release.url:
                console.print(f"  [link]{release.url}[/link]")

        if self._config.discord.enabled and self._config.discord.webhook_url:
            await self._send_release_discord(release, game_label)

    async def _send_release_discord(self, release: ProductRelease, game_label: str) -> None:
        game_colors = {
            "Pokemon": 0xFFCB05,
            "One Piece": 0xE21B23,
        }
        color = game_colors.get(game_label, 0x9B59B6)

        embed: dict = {
            "title": f"New {game_label} TCG Release",
            "description": release.title,
            "url": release.url,
            "color": color,
            "fields": [],
        }

        if release.release_date:
            embed["fields"].append({"name": "Release Date", "value": release.release_date, "inline": True})
        if release.price:
            embed["fields"].append({"name": "Price", "value": release.price, "inline": True})
        if release.product_type:
            embed["fields"].append({"name": "Type", "value": release.product_type, "inline": True})
        if release.image_url:
            embed["thumbnail"] = {"url": release.image_url}

        payload = {"embeds": [embed]}
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._config.discord.webhook_url,
                    json=payload,
                    timeout=10,
                )
                if resp.status_code not in (200, 204):
                    console.print(f"[yellow]Discord webhook returned {resp.status_code}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Discord release notification failed: {e}[/yellow]")

    async def notify_error(self, message: str) -> None:
        await self._send(f"ERROR: {message}", color=0xFF6600)

    async def notify_status(self, message: str) -> None:
        await self._send(message, color=0x3498DB)

    async def _send(self, message: str, color: int = 0xFFFFFF) -> None:
        if self._config.console.get("enabled", True):
            console.print(f"[bold]{message}[/bold]")

        if self._config.discord.enabled and self._config.discord.webhook_url:
            await self._send_discord(message, color)

    async def _send_discord(self, message: str, color: int) -> None:
        payload = {
            "embeds": [
                {
                    "title": "Card Checkout Bot",
                    "description": message,
                    "color": color,
                }
            ]
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self._config.discord.webhook_url,
                    json=payload,
                    timeout=10,
                )
                if resp.status_code not in (200, 204):
                    console.print(f"[yellow]Discord webhook returned {resp.status_code}[/yellow]")
        except Exception as e:
            console.print(f"[yellow]Discord notification failed: {e}[/yellow]")
