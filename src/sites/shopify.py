from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

import httpx
from rich.console import Console

from src.models import CheckoutAttempt, CheckoutResult, ProductInfo, ProductStatus, ProductTarget
from src.sites.base import SiteAdapter

if TYPE_CHECKING:
    from playwright.async_api import Page

console = Console()


class ShopifySiteAdapter(SiteAdapter):
    """Handles Shopify-based trading card stores."""

    name = "shopify"

    def matches_url(self, url: str) -> bool:
        return "myshopify.com" in url or "/products/" in url

    def _base_url(self, product_url: str) -> str:
        parsed = urlparse(product_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _product_handle(self, product_url: str) -> str:
        parsed = urlparse(product_url)
        parts = parsed.path.strip("/").split("/")
        if "products" in parts:
            idx = parts.index("products")
            if idx + 1 < len(parts):
                return parts[idx + 1]
        return parts[-1]

    async def check_stock(self, target: ProductTarget) -> ProductInfo:
        product_url = target.url
        base = self._base_url(product_url)
        handle = self._product_handle(product_url)
        json_url = f"{base}/products/{handle}.json"

        try:
            async with httpx.AsyncClient(
                proxies=self._proxy.get_httpx_proxy(),
                timeout=15,
                follow_redirects=True,
            ) as client:
                resp = await client.get(json_url)

                if resp.status_code == 200:
                    return self._parse_product_json(resp.json(), target)

                resp = await client.get(f"{base}/products/{handle}")
                if resp.status_code == 200:
                    return ProductInfo(
                        url=product_url,
                        status=ProductStatus.UNKNOWN,
                    )
        except Exception as e:
            console.print(f"[red]Stock check error: {e}[/red]")

        return ProductInfo(url=product_url, status=ProductStatus.UNKNOWN)

    def _parse_product_json(self, data: dict[str, Any], target: ProductTarget) -> ProductInfo:
        product = data.get("product", {})
        title = product.get("title", "")
        images = product.get("images", [])
        image_url = images[0]["src"] if images else ""

        variants = product.get("variants", [])
        if not variants:
            return ProductInfo(
                url=target.url,
                title=title,
                image_url=image_url,
                status=ProductStatus.OUT_OF_STOCK,
            )

        selected = variants[0]
        if target.size_or_variant:
            for v in variants:
                if target.size_or_variant.lower() in v.get("title", "").lower():
                    selected = v
                    break

        available = selected.get("available", False)
        price = float(selected.get("price", "0"))

        return ProductInfo(
            url=target.url,
            title=f"{title} — {selected.get('title', '')}".strip(" —"),
            price=price,
            status=ProductStatus.IN_STOCK if available else ProductStatus.OUT_OF_STOCK,
            variant_id=str(selected.get("id", "")),
            image_url=image_url,
        )

    async def checkout_http(self, target: ProductTarget, product: ProductInfo) -> CheckoutAttempt:
        start = time.monotonic()
        base = self._base_url(target.url)
        profile = self._settings.profile

        if not product.variant_id:
            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.ERROR,
                message="No variant ID available",
                duration_seconds=time.monotonic() - start,
            )

        try:
            async with httpx.AsyncClient(
                proxies=self._proxy.get_httpx_proxy(),
                timeout=self._settings.checkout.timeout_seconds,
                follow_redirects=True,
            ) as client:
                cart_resp = await client.post(
                    f"{base}/cart/add.js",
                    json={"id": int(product.variant_id), "quantity": target.quantity},
                )

                if cart_resp.status_code != 200:
                    return CheckoutAttempt(
                        product=product,
                        result=CheckoutResult.SOLD_OUT,
                        message=f"Add to cart failed: {cart_resp.status_code}",
                        duration_seconds=time.monotonic() - start,
                    )

                console.print("[green]Added to cart via HTTP[/green]")

                checkout_resp = await client.post(f"{base}/checkout")
                if checkout_resp.status_code not in (200, 302):
                    return CheckoutAttempt(
                        product=product,
                        result=CheckoutResult.ERROR,
                        message=f"Checkout init failed: {checkout_resp.status_code}",
                        duration_seconds=time.monotonic() - start,
                    )

                checkout_url = str(checkout_resp.url)

                shipping_data = {
                    "checkout[email]": profile.email,
                    "checkout[shipping_address][first_name]": profile.first_name,
                    "checkout[shipping_address][last_name]": profile.last_name,
                    "checkout[shipping_address][address1]": profile.address1,
                    "checkout[shipping_address][address2]": profile.address2,
                    "checkout[shipping_address][city]": profile.city,
                    "checkout[shipping_address][province]": profile.province,
                    "checkout[shipping_address][zip]": profile.zip,
                    "checkout[shipping_address][country]": profile.country,
                    "checkout[shipping_address][phone]": profile.phone,
                }

                await client.post(checkout_url, data=shipping_data)
                console.print("[green]Shipping info submitted[/green]")

                return CheckoutAttempt(
                    product=product,
                    result=CheckoutResult.SUCCESS,
                    message="Cart + shipping completed via HTTP. Payment requires browser.",
                    duration_seconds=time.monotonic() - start,
                )

        except httpx.TimeoutException:
            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.TIMEOUT,
                message="HTTP checkout timed out",
                duration_seconds=time.monotonic() - start,
            )
        except Exception as e:
            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.ERROR,
                message=str(e),
                duration_seconds=time.monotonic() - start,
            )

    async def checkout_browser(
        self, page: Page, target: ProductTarget, product: ProductInfo
    ) -> CheckoutAttempt:
        start = time.monotonic()
        profile = self._settings.profile
        payment = self._settings.payment

        try:
            await page.goto(target.url, wait_until="domcontentloaded", timeout=20000)

            if target.size_or_variant:
                try:
                    variant_selector = page.locator(
                        f'select option:has-text("{target.size_or_variant}")'
                    )
                    if await variant_selector.count() > 0:
                        parent_select = page.locator("select").first
                        await parent_select.select_option(label=target.size_or_variant)
                except Exception:
                    pass

            atc_selectors = [
                'button[name="add"]',
                'button:has-text("Add to cart")',
                'button:has-text("Add to Cart")',
                'input[type="submit"][name="add"]',
                'button.product-form__submit',
                'button[data-add-to-cart]',
            ]
            for sel in atc_selectors:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    console.print("[green]Clicked Add to Cart[/green]")
                    break
            else:
                return CheckoutAttempt(
                    product=product,
                    result=CheckoutResult.ERROR,
                    message="Could not find Add to Cart button",
                    duration_seconds=time.monotonic() - start,
                )

            await page.wait_for_timeout(1500)

            await page.goto(
                f"{self._base_url(target.url)}/checkout",
                wait_until="domcontentloaded",
                timeout=20000,
            )

            await self._fill_if_visible(page, 'input[name="checkout[email]"]', profile.email)
            await self._fill_if_visible(
                page, 'input[name="checkout[shipping_address][first_name]"]', profile.first_name
            )
            await self._fill_if_visible(
                page, 'input[name="checkout[shipping_address][last_name]"]', profile.last_name
            )
            await self._fill_if_visible(
                page, 'input[name="checkout[shipping_address][address1]"]', profile.address1
            )
            await self._fill_if_visible(
                page, 'input[name="checkout[shipping_address][city]"]', profile.city
            )
            await self._fill_if_visible(
                page, 'input[name="checkout[shipping_address][zip]"]', profile.zip
            )
            await self._fill_if_visible(
                page, 'input[name="checkout[shipping_address][phone]"]', profile.phone
            )

            continue_btn = page.locator('button:has-text("Continue")').first
            if await continue_btn.count() > 0:
                await continue_btn.click()
                await page.wait_for_timeout(2000)

            shipping_continue = page.locator('button:has-text("Continue")').first
            if await shipping_continue.count() > 0:
                await shipping_continue.click()
                await page.wait_for_timeout(2000)

            payment_frame = page.frame_locator(
                'iframe[id*="card-fields-number"]'
            )
            card_input = payment_frame.locator('input[name="number"]')
            if await card_input.count() > 0:
                await card_input.fill(payment.card_number)

            name_frame = page.frame_locator('iframe[id*="card-fields-name"]')
            name_input = name_frame.locator('input[name="name"]')
            if await name_input.count() > 0:
                await name_input.fill(payment.card_name)

            expiry_frame = page.frame_locator('iframe[id*="card-fields-expiry"]')
            expiry_input = expiry_frame.locator('input[name="expiry"]')
            if await expiry_input.count() > 0:
                await expiry_input.fill(
                    f"{payment.card_expiry_month}/{payment.card_expiry_year[-2:]}"
                )

            cvv_frame = page.frame_locator('iframe[id*="card-fields-verification"]')
            cvv_input = cvv_frame.locator('input[name="verification_value"]')
            if await cvv_input.count() > 0:
                await cvv_input.fill(payment.card_cvv)

            pay_btn_selectors = [
                'button:has-text("Pay now")',
                'button:has-text("Complete order")',
                'button[data-testid="step-footer-continue-btn"]',
            ]
            for sel in pay_btn_selectors:
                btn = page.locator(sel).first
                if await btn.count() > 0 and await btn.is_visible():
                    await btn.click()
                    console.print("[green]Payment submitted[/green]")
                    break

            await page.wait_for_timeout(5000)

            if "thank" in (await page.title()).lower() or "/thank_you" in page.url:
                order_text = await page.text_content("body")
                order_num = ""
                if "order" in (order_text or "").lower():
                    import re
                    match = re.search(r"#(\d+)", order_text or "")
                    if match:
                        order_num = match.group(1)

                return CheckoutAttempt(
                    product=product,
                    result=CheckoutResult.SUCCESS,
                    order_number=order_num,
                    message="Checkout completed via browser",
                    duration_seconds=time.monotonic() - start,
                )

            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.PAYMENT_FAILED,
                message="Could not confirm order completion",
                duration_seconds=time.monotonic() - start,
            )

        except Exception as e:
            return CheckoutAttempt(
                product=product,
                result=CheckoutResult.ERROR,
                message=str(e),
                duration_seconds=time.monotonic() - start,
            )

    async def _fill_if_visible(self, page: Page, selector: str, value: str) -> None:
        if not value:
            return
        el = page.locator(selector).first
        if await el.count() > 0 and await el.is_visible():
            await el.fill(value)
