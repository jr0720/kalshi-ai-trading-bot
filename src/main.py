from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console
from rich.panel import Panel

from src.config import load_settings
from src.monitor import ProductMonitor

console = Console()


def print_banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]Card Checkout Bot[/bold cyan]\n"
            "[dim]Automated trading card checkout[/dim]",
            border_style="cyan",
        )
    )


async def run_monitor(config_path: str) -> None:
    settings = load_settings(config_path)
    monitor = ProductMonitor(settings)
    await monitor.run()


async def run_single_check(config_path: str) -> None:
    from src.captcha_solver import CaptchaSolver
    from src.models import ProductTarget
    from src.monitor import get_adapter
    from src.proxy_manager import ProxyManager

    settings = load_settings(config_path)
    proxy = ProxyManager(settings.proxies)
    captcha = CaptchaSolver(settings.captcha)

    for p in settings.products:
        target = ProductTarget(
            url=p.url,
            size_or_variant=p.size_or_variant,
            max_price=p.max_price,
            quantity=p.quantity,
        )
        adapter = get_adapter(target.url, settings, proxy, captcha)
        product = await adapter.check_stock(target)
        console.print(
            f"[bold]{product.title or target.url}[/bold]: "
            f"{product.status.value} — ${product.price:.2f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Card Checkout Bot")
    parser.add_argument(
        "-c", "--config",
        default="config/settings.yaml",
        help="Path to settings YAML file",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("monitor", help="Monitor products and auto-checkout when in stock")
    sub.add_parser("check", help="One-time stock check on all configured products")

    args = parser.parse_args()

    print_banner()

    if args.command == "check":
        asyncio.run(run_single_check(args.config))
    elif args.command == "monitor":
        try:
            asyncio.run(run_monitor(args.config))
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped by user[/yellow]")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
