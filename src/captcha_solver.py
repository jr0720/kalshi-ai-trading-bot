from __future__ import annotations

import asyncio

from rich.console import Console

from src.config import CaptchaConfig

console = Console()


class CaptchaSolver:
    def __init__(self, config: CaptchaConfig):
        self._config = config
        self._solver = None

        if config.enabled:
            self._init_solver()

    def _init_solver(self) -> None:
        if self._config.provider == "2captcha":
            try:
                from twocaptcha import TwoCaptcha  # provided by 2captcha-python
                self._solver = TwoCaptcha(self._config.api_key)
                console.print("[green]2Captcha solver initialized[/green]")
            except ImportError:
                console.print("[red]twocaptcha-python not installed[/red]")
        else:
            console.print(f"[red]Unknown CAPTCHA provider: {self._config.provider}[/red]")

    @property
    def enabled(self) -> bool:
        return self._config.enabled and self._solver is not None

    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> str | None:
        if not self.enabled:
            return None

        console.print("[yellow]Solving reCAPTCHA v2...[/yellow]")
        try:
            result = await asyncio.to_thread(
                self._solver.recaptcha,
                sitekey=site_key,
                url=page_url,
            )
            token = result.get("code", "")
            if token:
                console.print("[green]reCAPTCHA v2 solved[/green]")
                return token
        except Exception as e:
            console.print(f"[red]CAPTCHA solve failed: {e}[/red]")
        return None

    async def solve_recaptcha_v3(
        self, site_key: str, page_url: str, action: str = "verify", min_score: float = 0.7
    ) -> str | None:
        if not self.enabled:
            return None

        console.print("[yellow]Solving reCAPTCHA v3...[/yellow]")
        try:
            result = await asyncio.to_thread(
                self._solver.recaptcha,
                sitekey=site_key,
                url=page_url,
                version="v3",
                action=action,
                score=min_score,
            )
            token = result.get("code", "")
            if token:
                console.print("[green]reCAPTCHA v3 solved[/green]")
                return token
        except Exception as e:
            console.print(f"[red]CAPTCHA solve failed: {e}[/red]")
        return None

    async def solve_hcaptcha(self, site_key: str, page_url: str) -> str | None:
        if not self.enabled:
            return None

        console.print("[yellow]Solving hCaptcha...[/yellow]")
        try:
            result = await asyncio.to_thread(
                self._solver.hcaptcha,
                sitekey=site_key,
                url=page_url,
            )
            token = result.get("code", "")
            if token:
                console.print("[green]hCaptcha solved[/green]")
                return token
        except Exception as e:
            console.print(f"[red]CAPTCHA solve failed: {e}[/red]")
        return None
