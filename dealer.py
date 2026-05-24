"""Dealer class that manages the deck and card dealing."""

from __future__ import annotations

from typing import List

from card import Card
from deck import Deck
from player import Player


class Dealer:
    """Deal cards and maintain the current deck."""

    def __init__(self) -> None:
        """Create a dealer with a new deck."""
        self.deck = Deck()

    def reset_deck(self) -> None:
        """Create and shuffle a fresh deck."""
        self.deck.reset()

    def deal_hole_cards(self, players: List[Player]) -> None:
        """Deal two private cards to every active player."""
        for _ in range(2):
            for player in players:
                if player.chips > 0:
                    player.receive_cards(self.deck.deal(1))

    def deal_flop(self) -> List[Card]:
        """Burn one card and deal the three-card flop."""
        self.burn()
        return self.deck.deal(3)

    def deal_turn_or_river(self) -> List[Card]:
        """Burn one card and deal one community card."""
        self.burn()
        return self.deck.deal(1)

    def burn(self) -> None:
        """Burn one card before revealing community cards."""
        if self.deck.cards_left > 0:
            self.deck.deal(1)

    def collect_cards(self, players: List[Player]) -> None:
        """Remove all private cards from players after the hand."""
        for player in players:
            player.hand.clear()
