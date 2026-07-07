from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console

from src.releases.models import ProductRelease

console = Console()

SEEN_FILE = "data/seen_releases.json"


class ReleaseTracker:
    """Persists which releases we've already seen so we only notify on new ones."""

    def __init__(self, path: str = SEEN_FILE):
        self._path = Path(path)
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
                self._seen = set(data.get("seen", []))
            except (json.JSONDecodeError, KeyError):
                self._seen = set()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"seen": sorted(self._seen)}, indent=2))

    def is_new(self, release: ProductRelease) -> bool:
        return release.key not in self._seen

    def mark_seen(self, release: ProductRelease) -> None:
        self._seen.add(release.key)
        self._save()

    def filter_new(self, releases: list[ProductRelease]) -> list[ProductRelease]:
        new = [r for r in releases if self.is_new(r)]
        return new

    @property
    def seen_count(self) -> int:
        return len(self._seen)
