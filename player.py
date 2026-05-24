"""Player classes for human and bot participants."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

from card import Card
from hand_evaluator import HandEvaluator


class PlayerActionError(ValueError):
    """Raised when a player tries to perform an invalid poker action."""


@dataclass
class Decision:
    """Represent a bot decision.

    Attributes:
        action: Action identifier: check, call, bet, all_in, or fold.
        amount: Target street bet for bet/raise actions.
    """

    action: str
    amount: int = 0


class Player:
    """Base class for a poker player.

    The class stores chips, hole cards and betting state.
    It intentionally does not know anything about Pygame.
    """

    def __init__(self, name: str, chips: int) -> None:
        """Initialize a player with a name and chip stack."""
        self.name = name
        self.chips = chips
        self.hand: List[Card] = []
        self.folded = False
        self.all_in = False
        self.current_bet = 0
        self.total_contribution = 0
        self.has_acted = False
        self.last_action = ""

    @property
    def is_active_in_hand(self) -> bool:
        """Return True if the player still contests the current hand."""
        return not self.folded and (self.all_in or self.chips > 0 or self.current_bet > 0)

    @property
    def can_act(self) -> bool:
        """Return True if the player can make a betting decision."""
        return not self.folded and not self.all_in and self.chips > 0

    def reset_for_hand(self) -> None:
        """Prepare the player for a new hand."""
        self.hand.clear()
        self.folded = False
        self.all_in = False
        self.current_bet = 0
        self.total_contribution = 0
        self.has_acted = False
        self.last_action = ""

    def reset_for_street(self) -> None:
        """Reset street-specific betting state."""
        self.current_bet = 0
        self.has_acted = False
        self.last_action = ""

    def receive_cards(self, cards: List[Card]) -> None:
        """Add dealt cards to the player's hand."""
        self.hand.extend(cards)

    def fold(self) -> None:
        """Fold the current hand."""
        self.folded = True
        self.has_acted = True
        self.last_action = "фолд"

    def check(self) -> None:
        """Check without adding chips to the pot."""
        if self.folded:
            raise PlayerActionError("Folded player cannot check.")
        self.has_acted = True
        self.last_action = "чек"

    def bet(self, amount: int) -> int:
        """Put additional chips into the pot.

        Args:
            amount: Amount to add from the player's stack.

        Returns:
            Actual amount added. It may be smaller if the player goes all-in.
        """
        if amount <= 0:
            raise PlayerActionError("Bet amount must be positive.")
        if self.folded:
            raise PlayerActionError("Folded player cannot bet.")

        actual = min(amount, self.chips)
        self.chips -= actual
        self.current_bet += actual
        self.total_contribution += actual
        if self.chips == 0:
            self.all_in = True
        self.has_acted = True
        self.last_action = f"ставка {actual}"
        return actual

    def call(self, current_bet: int) -> int:
        """Call the current street bet.

        Args:
            current_bet: Highest current bet on this street.

        Returns:
            Actual amount added to the pot.
        """
        amount_to_call = max(0, current_bet - self.current_bet)
        if amount_to_call == 0:
            self.check()
            return 0

        actual = self.bet(amount_to_call)
        self.last_action = f"колл {actual}"
        return actual

    def all_in_move(self) -> int:
        """Move all remaining chips into the pot."""
        if self.chips <= 0:
            raise PlayerActionError("Player has no chips for all-in.")
        actual = self.bet(self.chips)
        self.all_in = True
        self.last_action = f"олл-ин {actual}"
        return actual


class HumanPlayer(Player):
    """Player controlled by the human through the GUI."""


class BotPlayer(Player):
    """Simple AI-controlled poker player."""

    def make_decision(self, state: Dict[str, object]) -> Decision:
        """Choose a poker action using simple hand strength and randomness.

        Args:
            state: Dictionary with current_bet, community_cards, min_raise,
                big_blind, and pot values.

        Returns:
            Decision object with action and optional amount.
        """
        current_bet = int(state["current_bet"])
        min_raise = int(state["min_raise"])
        community_cards = list(state["community_cards"])
        call_amount = max(0, current_bet - self.current_bet)

        strength = self._estimate_strength(community_cards)
        randomness = random.random()

        if call_amount >= self.chips:
            if strength > 0.72 or randomness < 0.07:
                return Decision("all_in")
            if strength > 0.55 and randomness < 0.65:
                return Decision("call")
            return Decision("fold")

        if call_amount == 0:
            if strength > 0.74 and randomness < 0.45:
                return self._raise_decision(current_bet, min_raise, aggressive=True)
            if strength > 0.58 and randomness < 0.20:
                return self._raise_decision(current_bet, min_raise, aggressive=False)
            return Decision("check")

        if strength < 0.36 and randomness < 0.70:
            return Decision("fold")
        if strength > 0.80 and randomness < 0.25:
            return Decision("all_in")
        if strength > 0.66 and randomness < 0.45:
            return self._raise_decision(current_bet, min_raise, aggressive=True)
        if strength > 0.45 or randomness < 0.25:
            return Decision("call")
        return Decision("fold")

    def _estimate_strength(self, community_cards: List[Card]) -> float:
        """Estimate the strength of bot cards and community cards."""
        if len(community_cards) >= 3:
            return HandEvaluator.quick_strength(self.hand + community_cards)
        return HandEvaluator.quick_strength(self.hand)

    def _raise_decision(self, current_bet: int, min_raise: int, aggressive: bool) -> Decision:
        """Create a raise decision, occasionally choosing all-in."""
        if self.chips <= min_raise:
            return Decision("all_in")

        multiplier = random.randint(2, 4) if aggressive else random.randint(1, 2)
        target = current_bet + min_raise * multiplier
        max_target = self.current_bet + self.chips
        target = min(target, max_target)

        if target >= max_target and random.random() < 0.35:
            return Decision("all_in")
        return Decision("bet", target)
