from __future__ import annotations

import enum
from dataclasses import dataclass


class CardGame(enum.Enum):
    POKEMON = "pokemon"
    ONE_PIECE = "one_piece"


@dataclass
class ProductRelease:
    game: CardGame
    title: str
    url: str
    release_date: str = ""
    price: str = ""
    description: str = ""
    image_url: str = ""
    product_type: str = ""

    @property
    def key(self) -> str:
        return f"{self.game.value}:{self.url}"
