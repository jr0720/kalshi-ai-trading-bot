from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

    from src.captcha_solver import CaptchaSolver
    from src.config import Settings
    from src.models import CheckoutAttempt, ProductInfo, ProductTarget
    from src.proxy_manager import ProxyManager


class SiteAdapter(abc.ABC):
    """Base class for site-specific checkout logic."""

    name: str = "unknown"

    def __init__(self, settings: Settings, proxy_manager: ProxyManager, captcha_solver: CaptchaSolver):
        self._settings = settings
        self._proxy = proxy_manager
        self._captcha = captcha_solver

    @abc.abstractmethod
    def matches_url(self, url: str) -> bool:
        """Return True if this adapter handles the given URL."""
        ...

    @abc.abstractmethod
    async def check_stock(self, target: ProductTarget) -> ProductInfo:
        """Check if the product is in stock. Uses HTTP where possible."""
        ...

    @abc.abstractmethod
    async def checkout_http(self, target: ProductTarget, product: ProductInfo) -> CheckoutAttempt:
        """Attempt checkout via direct HTTP requests."""
        ...

    @abc.abstractmethod
    async def checkout_browser(
        self, page: Page, target: ProductTarget, product: ProductInfo
    ) -> CheckoutAttempt:
        """Attempt checkout via browser automation."""
        ...
