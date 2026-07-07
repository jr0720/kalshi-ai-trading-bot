from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from rich.console import Console

from src.models import CheckoutAttempt, CheckoutResult, ProductInfo, ProductStatus, ProductTarget
from src.sites.base import SiteAdapter

if TYPE_CHECKING:
    from playwright.async_api import Page

console = Console()


class GenericSiteAdapter(SiteAdapter):
    """Fallback adapter that uses browser automation for any site."""

    name = "generic"

    def matches_url(self, url: str) -> bool:
        return True

    async def check_stock(self, target: ProductTarget) -> ProductInfo:
        """
        Generic stock check via browser — looks for common out-of-stock indicators.
        Falls back to UNKNOWN if it can't determine availability.
        """
        import httpx

        try:
            async with httpx.AsyncClient(
                proxies=self._proxy.get_httpx_proxy(),
                timeout=15,
                follow_redirects=True,
            ) as client:
                resp = await client.get(target.url)
                body = resp.text.lower()

                out_of_stock_signals = [
                    "out of stock",
                    "sold out",
                    "currently unavailable",
                    "not available",
                    "coming soon",
                    "notify me",
                    "pre-order",
                ]

                in_stock_signals = [
                    "add to cart",
                    "add to bag",
                    "buy now",
                    "in stock",
                ]

                has_oos = any(s in body for s in out_of_stock_signals)
                has_is = any(s in body for s in in_stock_signals)

                title_match = re.search(r"<title>(.*?)</title>", body)
                title = title_match.group(1) if title_match else ""

                price = 0.0
                price_match = re.search(r'\$(\d+(?:\.\d{2})?)', resp.text)
                if price_match:
                    price = float(price_match.group(1))

                if has_is and not has_oos:
                    status = ProductStatus.IN_STOCK
                elif has_oos:
                    status = ProductStatus.OUT_OF_STOCK
                else:
                    status = ProductStatus.UNKNOWN

                return ProductInfo(
                    url=target.url,
                    title=title,
                    price=price,
                    status=status,
                )
        except Exception as e:
            console.print(f"[red]Generic stock check error: {e}[/red]")
            return ProductInfo(url=target.url, status=ProductStatus.UNKNOWN)

    async def checkout_http(self, target: ProductTarget, product: ProductInfo) -> CheckoutAttempt:
        return CheckoutAttempt(
            product=product,
            result=CheckoutResult.ERROR,
            message="Generic adapter does not support HTTP checkout. Use browser mode.",
        )

    async def checkout_browser(
        self, page: Page, target: ProductTarget, product: ProductInfo
    ) -> CheckoutAttempt:
        start = time.monotonic()
        profile = self._settings.profile

        try:
            await page.goto(target.url, wait_until="domcontentloaded", timeout=20000)

            atc_patterns = [
                'button:has-text("Add to Cart")',
                'button:has-text("Add to Bag")',
                'button:has-text("Buy Now")',
                'button:has-text("Add To Cart")',
                'input[value*="Add to Cart" i]',
                'a:has-text("Add to Cart")',
                '[data-action="add-to-cart"]',
            ]

            clicked = False
            for sel in atc_patterns:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    console.print(f"[green]Clicked ATC: {sel}[/green]")
                    clicked = True
                    break

            if not clicked:
                return CheckoutAttempt(
                    product=product,
                    result=CheckoutResult.ERROR,
                    message="Could not find Add to Cart button on this site",
                    duration_seconds=time.monotonic() - start,
                )

            await page.wait_for_timeout(2000)

            checkout_links = [
                'a:has-text("Checkout")',
                'a:has-text("Check Out")',
                'button:has-text("Checkout")',
                'button:has-text("Proceed to Checkout")',
                'a[href*="checkout"]',
            ]

            for sel in checkout_links:
                link = page.locator(sel).first
                if await link.count() > 0 and await link.is_visible():
                    await link.click()
                    console.print(f"[green]Navigating to checkout: {sel}[/green]")
                    break

            await page.wait_for_timeout(3000)

            field_map = {
                'input[name*="email" i]': profile.email,
                'input[name*="first" i][name*="name" i]': profile.first_name,
                'input[name*="last" i][name*="name" i]': profile.last_name,
                'input[name*="address" i][name*="1" i]': profile.address1,
                'input[name*="city" i]': profile.city,
                'input[name*="zip" i], input[name*="postal" i]': profile.zip,
                'input[name*="phone" i], input[type="tel"]': profile.phone,
            }

            for selector, value in field_map.items():
                if not value:
                    continue
                el = page.locator(selector).first
                if await el.count() > 0 and await el.is_visible():
                    await el.fill(value)

            console.print("[yellow]Generic checkout: filled shipping info. Payment step requires site-specific handling.[/yellow]")

            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.SUCCESS,
                message="Generic checkout: ATC + shipping info completed. Review browser for payment.",
                duration_seconds=time.monotonic() - start,
            )

        except Exception as e:
            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.ERROR,
                message=str(e),
                duration_seconds=time.monotonic() - start,
            )
