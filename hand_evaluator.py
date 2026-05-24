"""Poker hand evaluation utilities."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from card import Card


@dataclass(frozen=True)
class HandResult:
    """Represent an evaluated poker hand.

    Attributes:
        name: Russian name of the combination.
        score: Comparable tuple where the first item is the hand category.
        cards: Five cards that form the evaluated hand when possible.
    """

    name: str
    score: Tuple[int, ...]
    cards: Tuple[Card, ...]

    def __lt__(self, other: "HandResult") -> bool:
        """Compare two hand results by score."""
        return self.score < other.score

    def __eq__(self, other: object) -> bool:
        """Return True if two hand results have the same score."""
        if not isinstance(other, HandResult):
            return NotImplemented
        return self.score == other.score

    def description(self) -> str:
        """Return a readable hand description."""
        return f"{self.name} ({', '.join(str(card) for card in self.cards)})"


class HandEvaluator:
    """Evaluate Texas Hold'em combinations from five to seven cards."""

    HAND_NAMES: Dict[int, str] = {
        9: "Флеш-рояль",
        8: "Стрит-флеш",
        7: "Каре",
        6: "Фулл-хаус",
        5: "Флеш",
        4: "Стрит",
        3: "Сет",
        2: "Две пары",
        1: "Пара",
        0: "Старшая карта",
    }

    @staticmethod
    def evaluate(cards: Sequence[Card]) -> HandResult:
        """Evaluate the best five-card poker hand.

        Args:
            cards: A sequence containing from five to seven cards.

        Returns:
            Best hand result with comparable score.

        Raises:
            ValueError: If fewer than five cards are given.
        """
        if len(cards) < 5:
            raise ValueError("At least five cards are required for evaluation.")

        ordered = sorted(cards, key=lambda card: card.rank, reverse=True)
        ranks = [card.rank for card in ordered]
        rank_counter = Counter(ranks)
        cards_by_rank = defaultdict(list)
        cards_by_suit = defaultdict(list)

        for card in ordered:
            cards_by_rank[card.rank].append(card)
            cards_by_suit[card.suit].append(card)

        straight_flush = HandEvaluator._find_straight_flush(cards_by_suit)
        if straight_flush:
            high = HandEvaluator._straight_high(straight_flush)
            category = 9 if high == 14 else 8
            return HandResult(HandEvaluator.HAND_NAMES[category], (category, high), tuple(straight_flush))

        four_rank = HandEvaluator._ranks_with_count(rank_counter, 4)
        if four_rank:
            quad = four_rank[0]
            kicker = HandEvaluator._highest_excluding(ordered, [quad], 1)
            result_cards = tuple(cards_by_rank[quad][:4] + kicker)
            return HandResult(HandEvaluator.HAND_NAMES[7], (7, quad, kicker[0].rank), result_cards)

        full_house = HandEvaluator._find_full_house(rank_counter, cards_by_rank)
        if full_house:
            trips, pair, result_cards = full_house
            return HandResult(HandEvaluator.HAND_NAMES[6], (6, trips, pair), tuple(result_cards))

        flush = HandEvaluator._find_flush(cards_by_suit)
        if flush:
            return HandResult(HandEvaluator.HAND_NAMES[5], (5, *[card.rank for card in flush]), tuple(flush))

        straight = HandEvaluator._find_straight(ordered)
        if straight:
            high = HandEvaluator._straight_high(straight)
            return HandResult(HandEvaluator.HAND_NAMES[4], (4, high), tuple(straight))

        trips_ranks = HandEvaluator._ranks_with_count(rank_counter, 3)
        if trips_ranks:
            trips = trips_ranks[0]
            kickers = HandEvaluator._highest_excluding(ordered, [trips], 2)
            result_cards = tuple(cards_by_rank[trips][:3] + kickers)
            return HandResult(HandEvaluator.HAND_NAMES[3], (3, trips, *[card.rank for card in kickers]), result_cards)

        pairs = HandEvaluator._ranks_with_count(rank_counter, 2)
        if len(pairs) >= 2:
            high_pair, low_pair = pairs[:2]
            kicker = HandEvaluator._highest_excluding(ordered, [high_pair, low_pair], 1)
            result_cards = tuple(cards_by_rank[high_pair][:2] + cards_by_rank[low_pair][:2] + kicker)
            return HandResult(HandEvaluator.HAND_NAMES[2], (2, high_pair, low_pair, kicker[0].rank), result_cards)

        if len(pairs) == 1:
            pair = pairs[0]
            kickers = HandEvaluator._highest_excluding(ordered, [pair], 3)
            result_cards = tuple(cards_by_rank[pair][:2] + kickers)
            return HandResult(HandEvaluator.HAND_NAMES[1], (1, pair, *[card.rank for card in kickers]), result_cards)

        high_cards = ordered[:5]
        return HandResult(HandEvaluator.HAND_NAMES[0], (0, *[card.rank for card in high_cards]), tuple(high_cards))

    @staticmethod
    def quick_strength(cards: Sequence[Card]) -> float:
        """Return an approximate normalized strength between 0 and 1.

        The method is used by bots and intentionally keeps the strategy simple.
        """
        if len(cards) >= 5:
            result = HandEvaluator.evaluate(cards)
            category = result.score[0]
            high_part = sum(result.score[1:]) / 100.0
            return min(1.0, category / 9.0 + high_part / 20.0)

        if len(cards) == 2:
            first, second = cards
            ranks = sorted([first.rank, second.rank], reverse=True)
            strength = (ranks[0] + ranks[1]) / 28.0
            if first.rank == second.rank:
                strength += 0.28
            if first.suit == second.suit:
                strength += 0.08
            if abs(first.rank - second.rank) <= 2:
                strength += 0.06
            if ranks[0] >= 13:
                strength += 0.08
            return min(1.0, strength)

        return 0.0

    @staticmethod
    def _ranks_with_count(counter: Counter[int], count: int) -> List[int]:
        """Return ranks that appear at least count times, descending."""
        return sorted([rank for rank, total in counter.items() if total >= count], reverse=True)

    @staticmethod
    def _highest_excluding(cards: Sequence[Card], excluded_ranks: Iterable[int], count: int) -> List[Card]:
        """Return the highest cards whose ranks are not excluded."""
        excluded = set(excluded_ranks)
        return [card for card in cards if card.rank not in excluded][:count]

    @staticmethod
    def _find_flush(cards_by_suit: Dict[str, List[Card]]) -> List[Card] | None:
        """Find the highest available flush."""
        for suited_cards in cards_by_suit.values():
            if len(suited_cards) >= 5:
                return sorted(suited_cards, key=lambda card: card.rank, reverse=True)[:5]
        return None

    @staticmethod
    def _find_straight(cards: Sequence[Card]) -> List[Card] | None:
        """Find the highest straight among the given cards."""
        unique: Dict[int, Card] = {}
        for card in sorted(cards, key=lambda item: item.rank, reverse=True):
            unique.setdefault(card.rank, card)

        ranks = sorted(unique.keys(), reverse=True)
        if 14 in unique:
            ranks.append(1)
            unique[1] = unique[14]

        run: List[int] = []
        previous = None
        for rank in ranks:
            if previous is None or previous - 1 == rank:
                run.append(rank)
            elif previous != rank:
                run = [rank]

            if len(run) >= 5:
                selected_ranks = run[:5]
                return [unique[14 if rank == 1 else rank] for rank in selected_ranks]
            previous = rank

        return None

    @staticmethod
    def _find_straight_flush(cards_by_suit: Dict[str, List[Card]]) -> List[Card] | None:
        """Find the highest straight flush across all suits."""
        best: List[Card] | None = None
        for suited_cards in cards_by_suit.values():
            if len(suited_cards) >= 5:
                straight = HandEvaluator._find_straight(suited_cards)
                if straight and (best is None or HandEvaluator._straight_high(straight) > HandEvaluator._straight_high(best)):
                    best = straight
        return best

    @staticmethod
    def _find_full_house(
        counter: Counter[int],
        cards_by_rank: Dict[int, List[Card]],
    ) -> Tuple[int, int, List[Card]] | None:
        """Find the best full house and return involved ranks and cards."""
        trips_ranks = sorted([rank for rank, total in counter.items() if total >= 3], reverse=True)
        if not trips_ranks:
            return None

        trips = trips_ranks[0]
        pair_candidates = sorted(
            [rank for rank, total in counter.items() if rank != trips and total >= 2],
            reverse=True,
        )

        if not pair_candidates and len(trips_ranks) >= 2:
            pair_candidates.append(trips_ranks[1])

        if not pair_candidates:
            return None

        pair = pair_candidates[0]
        result_cards = cards_by_rank[trips][:3] + cards_by_rank[pair][:2]
        return trips, pair, result_cards

    @staticmethod
    def _straight_high(straight_cards: Sequence[Card]) -> int:
        """Return the high rank of a straight, accounting for wheel A-2-3-4-5."""
        ranks = sorted({card.rank for card in straight_cards}, reverse=True)
        if {14, 5, 4, 3, 2}.issubset(set(ranks)):
            return 5
        return max(ranks)
