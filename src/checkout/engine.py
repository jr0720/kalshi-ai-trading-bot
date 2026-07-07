from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from playwright.async_api import async_playwright
from rich.console import Console

from src.models import CheckoutAttempt, CheckoutResult, ProductInfo, ProductTarget
from src.sites.base import SiteAdapter

if TYPE_CHECKING:
    from src.captcha_solver import CaptchaSolver
    from src.config import Settings
    from src.notifications import Notifier
    from src.proxy_manager import ProxyManager

console = Console()


class CheckoutEngine:
    def __init__(
        self,
        settings: Settings,
        adapter: SiteAdapter,
        proxy_manager: ProxyManager,
        captcha_solver: CaptchaSolver,
        notifier: Notifier,
    ):
        self._settings = settings
        self._adapter = adapter
        self._proxy = proxy_manager
        self._captcha = captcha_solver
        self._notifier = notifier

    async def attempt_checkout(
        self, target: ProductTarget, product: ProductInfo
    ) -> CheckoutAttempt:
        mode = self._settings.checkout.mode
        max_retries = self._settings.checkout.retry_attempts

        for attempt_num in range(1, max_retries + 1):
            console.print(
                f"[cyan]Checkout attempt {attempt_num}/{max_retries} "
                f"for {product.title or product.url}[/cyan]"
            )

            if mode in ("auto", "http"):
                result = await self._try_http(target, product)
                if result.result == CheckoutResult.SUCCESS:
                    return result
                if mode == "auto":
                    console.print("[yellow]HTTP checkout incomplete, falling back to browser[/yellow]")

            if mode in ("auto", "browser"):
                result = await self._try_browser(target, product)
                if result.result == CheckoutResult.SUCCESS:
                    return result

            if attempt_num < max_retries:
                console.print("[yellow]Retrying in 2s...[/yellow]")
                await asyncio.sleep(2)

        return CheckoutAttempt(
            product=product,
            result=CheckoutResult.ERROR,
            message=f"All {max_retries} attempts failed",
        )

    async def _try_http(
        self, target: ProductTarget, product: ProductInfo
    ) -> CheckoutAttempt:
        try:
            return await self._adapter.checkout_http(target, product)
        except Exception as e:
            console.print(f"[red]HTTP checkout error: {e}[/red]")
            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.ERROR,
                message=str(e),
            )

    async def _try_browser(
        self, target: ProductTarget, product: ProductInfo
    ) -> CheckoutAttempt:
        try:
            async with async_playwright() as pw:
                browser_args = {}
                proxy_url = self._proxy.get_proxy()
                if proxy_url:
                    browser_args["proxy"] = {"server": proxy_url}

                browser = await pw.chromium.launch(
                    headless=self._settings.browser.headless,
                    **browser_args,
                )

                context_opts: dict = {}
                if self._settings.browser.user_agent:
                    context_opts["user_agent"] = self._settings.browser.user_agent

                context = await browser.new_context(**context_opts)
                page = await context.new_page()

                try:
                    result = await self._adapter.checkout_browser(page, target, product)
                    return result
                finally:
                    await browser.close()

        except Exception as e:
            console.print(f"[red]Browser checkout error: {e}[/red]")
            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.ERROR,
                message=str(e),
            )
