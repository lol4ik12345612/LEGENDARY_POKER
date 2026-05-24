"""Deck model for Texas Hold'em poker."""

from __future__ import annotations

import random
from typing import List

from card import Card
from constants import SUITS


class Deck:
    """Represent a standard shuffled 52-card deck."""

    def __init__(self) -> None:
        """Create a new ordered deck and shuffle it."""
        self._cards: List[Card] = []
        self.reset()

    @property
    def cards_left(self) -> int:
        """Return the number of cards currently left in the deck."""
        return len(self._cards)

    def reset(self) -> None:
        """Rebuild a full 52-card deck and shuffle it."""
        self._cards = [Card(suit, rank) for suit in SUITS for rank in range(2, 15)]
        self.shuffle()

    def shuffle(self) -> None:
        """Shuffle all cards in the deck in-place."""
        random.shuffle(self._cards)

    def deal(self, count: int = 1) -> List[Card]:
        """Deal and remove a given number of cards from the deck.

        Args:
            count: Number of cards to deal.

        Returns:
            List of dealt cards.

        Raises:
            ValueError: If there are not enough cards.
        """
        if count < 1:
            raise ValueError("Count must be positive.")
        if count > len(self._cards):
            raise ValueError("Not enough cards in the deck.")

        dealt = self._cards[:count]
        del self._cards[:count]
        return dealt
