from __future__ import annotations

import itertools
import random
from pathlib import Path

from rich.console import Console

from src.config import ProxyConfig
from src.models import ProxyEntry

console = Console()


class ProxyManager:
    def __init__(self, config: ProxyConfig):
        self._config = config
        self._proxies: list[ProxyEntry] = []
        self._cycle: itertools.cycle[ProxyEntry] | None = None

        if config.enabled:
            self._load_proxies()

    def _load_proxies(self) -> None:
        proxy_file = Path(self._config.file)
        if not proxy_file.exists():
            console.print(f"[yellow]Proxy file not found: {proxy_file}[/yellow]")
            return

        lines = proxy_file.read_text().strip().splitlines()
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                self._proxies.append(ProxyEntry(url=line))

        console.print(f"[green]Loaded {len(self._proxies)} proxies[/green]")
        if self._proxies:
            self._cycle = itertools.cycle(self._proxies)

    @property
    def enabled(self) -> bool:
        return self._config.enabled and len(self._proxies) > 0

    def get_proxy(self) -> str | None:
        if not self.enabled:
            return None

        active = [p for p in self._proxies if not p.is_banned]
        if not active:
            console.print("[red]All proxies are banned![/red]")
            return None

        if self._config.rotation == "random":
            return random.choice(active).url

        if self._config.rotation == "round_robin" and self._cycle:
            for _ in range(len(self._proxies)):
                entry = next(self._cycle)
                if not entry.is_banned:
                    return entry.url

        return active[0].url

    def get_httpx_proxy(self) -> dict[str, str] | None:
        proxy_url = self.get_proxy()
        if not proxy_url:
            return None
        return {"all://": proxy_url}

    def mark_failure(self, proxy_url: str, ban_threshold: int = 5) -> None:
        for p in self._proxies:
            if p.url == proxy_url:
                p.failures += 1
                if p.failures >= ban_threshold:
                    p.is_banned = True
                    console.print(f"[red]Proxy banned after {ban_threshold} failures: {proxy_url}[/red]")
                break

    def reset_proxy(self, proxy_url: str) -> None:
        for p in self._proxies:
            if p.url == proxy_url:
                p.failures = 0
                p.is_banned = False
                break

    @property
    def proxy_count(self) -> int:
        return len(self._proxies)

    @property
    def active_count(self) -> int:
        return len([p for p in self._proxies if not p.is_banned])
