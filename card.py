from __future__ import annotations
from dataclasses import dataclass
from constants import RANK_LABELS, RANK_RU, SUIT_RU, SUIT_SYMBOLS

@dataclass(frozen=True)
class Card:

    suit: str
    rank: int

    def __post_init__(self) -> None:
        if self.suit not in SUIT_SYMBOLS:
            raise ValueError(f"Unknown suit: {self.suit}")
        if self.rank not in RANK_LABELS:
            raise ValueError(f"Unknown rank: {self.rank}")

    @property
    def label(self) -> str:
        return RANK_LABELS[self.rank]

    @property
    def symbol(self) -> str:
        return SUIT_SYMBOLS[self.suit]

    @property
    def is_red(self) -> bool:
        return self.suit in {"hearts", "diamonds"}

    def image_key(self) -> str:
        return f"{self.label}_of_{self.suit}".lower()

    def __lt__(self, other: "Card") -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return (self.rank, self.suit) < (other.rank, other.suit)

    def __str__(self) -> str:
        return f"{self.label}{self.symbol}"

    def full_name(self) -> str:
        return f"{RANK_RU[self.rank]} {SUIT_RU[self.suit]}"
