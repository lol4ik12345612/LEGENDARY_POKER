"""Core Texas Hold'em game controller."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from card import Card
from constants import BIG_BLIND, SMALL_BLIND
from dealer import Dealer
from hand_evaluator import HandEvaluator, HandResult
from player import BotPlayer, HumanPlayer, Player, PlayerActionError


@dataclass
class PotAward:
    """Represent a distributed pot award after showdown."""

    amount: int
    winners: List[Player]
    hand_result: Optional[HandResult]


class PokerGame:
    """Control the complete Texas Hold'em rules and hand flow."""

    STAGES = ("preflop", "flop", "turn", "river")

    def __init__(self, player_count: int, starting_chips: int) -> None:
        """Create a new poker game.

        Args:
            player_count: Total number of players from 2 to 6.
            starting_chips: Initial stack for every player.
        """
        if not 2 <= player_count <= 6:
            raise ValueError("Player count must be between 2 and 6.")
        if starting_chips < BIG_BLIND * 5:
            raise ValueError("Starting chips are too low for the selected blinds.")

        self.players: List[Player] = [HumanPlayer("Вы", starting_chips)]
        self.players.extend(BotPlayer(f"Бот {index}", starting_chips) for index in range(1, player_count))

        self.dealer = Dealer()
        self.dealer_position = -1
        self.small_blind = SMALL_BLIND
        self.big_blind = BIG_BLIND

        self.community_cards: List[Card] = []
        self.stage = "menu"
        self.current_bet = 0
        self.min_raise = self.big_blind
        self.current_player_index = 0
        self.message_log: List[str] = []
        self.awards: List[PotAward] = []
        self.showdown_results: Dict[Player, HandResult] = {}
        self.hand_number = 0
        self.game_winner: Optional[Player] = None

        self.start_new_hand()

    @property
    def pot(self) -> int:
        """Return the total amount currently committed to the pot."""
        return sum(player.total_contribution for player in self.players)

    @property
    def human_player(self) -> HumanPlayer:
        """Return the human player."""
        return self.players[0]  # type: ignore[return-value]

    @property
    def active_player(self) -> Player:
        """Return the player whose turn is currently active."""
        return self.players[self.current_player_index]

    def start_new_hand(self) -> None:
        """Start a new hand if the game is not finished."""
        self._remove_empty_players_from_hand()
        winner = self._single_remaining_stack_player()
        if winner:
            self.game_winner = winner
            self.stage = "game_over"
            self._log(f"Игра окончена. Победитель: {winner.name}.")
            return

        self.hand_number += 1
        self.community_cards.clear()
        self.awards.clear()
        self.showdown_results.clear()
        self.current_bet = 0
        self.min_raise = self.big_blind
        self.message_log = [f"Раздача №{self.hand_number} началась."]

        for player in self.players:
            player.reset_for_hand()
            if player.chips <= 0:
                player.folded = True
                player.all_in = True

        self.dealer.reset_deck()
        self.dealer_position = self._next_index_with_chips(self.dealer_position)
        active_players = [player for player in self.players if player.chips > 0]
        self.dealer.deal_hole_cards(active_players)

        self._post_blinds()
        self.stage = "preflop"
        self.current_player_index = self._first_to_act_preflop()
        self._skip_to_next_player_if_needed()

    def get_state_for_bot(self) -> Dict[str, object]:
        """Return a compact immutable-style state dictionary for bot decisions."""
        return {
            "stage": self.stage,
            "current_bet": self.current_bet,
            "min_raise": self.min_raise,
            "big_blind": self.big_blind,
            "pot": self.pot,
            "community_cards": tuple(self.community_cards),
        }

    def get_available_actions(self, player: Optional[Player] = None) -> Dict[str, object]:
        """Return action availability and call amount for the given player."""
        player = player or self.active_player
        call_amount = max(0, self.current_bet - player.current_bet)
        can_check = call_amount == 0
        return {
            "check": player.can_act and can_check,
            "call": player.can_act and call_amount > 0,
            "bet": player.can_act and player.chips > call_amount,
            "all_in": player.can_act and player.chips > 0,
            "fold": player.can_act,
            "call_amount": call_amount,
            "min_bet": self.current_bet + self.min_raise if self.current_bet else self.big_blind,
        }

    def handle_human_action(self, action: str, amount: int = 0) -> None:
        """Apply an action chosen by the human player."""
        if self.stage not in self.STAGES:
            return
        if not isinstance(self.active_player, HumanPlayer):
            return
        self.apply_action(self.active_player, action, amount)

    def process_bot_turn(self) -> None:
        """Let the active bot make and apply a decision."""
        if self.stage not in self.STAGES:
            return
        player = self.active_player
        if not isinstance(player, BotPlayer):
            return

        decision = player.make_decision(self.get_state_for_bot())
        self.apply_action(player, decision.action, decision.amount)

    def apply_action(self, player: Player, action: str, amount: int = 0) -> None:
        """Apply a player action and advance the game.

        Args:
            player: Player who performs the action.
            action: Action identifier.
            amount: Target street bet for bet/raise action.
        """
        if player is not self.active_player:
            return

        try:
            previous_bet = self.current_bet

            if action == "fold":
                player.fold()
                self._log(f"{player.name}: фолд.")

            elif action == "check":
                if player.current_bet != self.current_bet:
                    self._log(f"{player.name} не может сделать чек: нужно коллировать {self.current_bet - player.current_bet}.")
                    return
                player.check()
                self._log(f"{player.name}: чек.")

            elif action == "call":
                added = player.call(self.current_bet)
                self._log(f"{player.name}: колл {added}.")

            elif action == "bet":
                self._apply_bet_or_raise(player, amount, previous_bet)

            elif action == "all_in":
                self._apply_all_in(player, previous_bet)

            else:
                self._log("Неизвестное действие.")
                return

        except PlayerActionError as error:
            self._log(str(error))
            return

        if self._only_one_player_not_folded():
            self._finish_by_fold()
            return

        if self._betting_round_finished():
            self._advance_stage()
        else:
            self._move_to_next_actor()

    def _apply_bet_or_raise(self, player: Player, target_street_bet: int, previous_bet: int) -> None:
        """Apply a bet or raise to the target street amount."""
        min_target = self.big_blind if self.current_bet == 0 else self.current_bet + self.min_raise
        if target_street_bet < min_target:
            self._log(f"Минимальная ставка/рейз: {min_target}.")
            return

        additional = target_street_bet - player.current_bet
        if additional <= 0:
            self._log("Сумма ставки должна увеличивать текущую ставку.")
            return

        added = player.bet(additional)
        if player.current_bet > self.current_bet:
            self.current_bet = player.current_bet
            self.min_raise = max(self.big_blind, self.current_bet - previous_bet)
            self._mark_others_need_action(player)
            self._log(f"{player.name}: ставка/рейз до {player.current_bet} (+{added}).")
        else:
            self._log(f"{player.name}: ставка {added}.")

    def _apply_all_in(self, player: Player, previous_bet: int) -> None:
        """Apply an all-in action."""
        added = player.all_in_move()
        if player.current_bet > self.current_bet:
            self.current_bet = player.current_bet
            self.min_raise = max(self.big_blind, self.current_bet - previous_bet)
            self._mark_others_need_action(player)
        self._log(f"{player.name}: олл-ин {added}.")

    def _post_blinds(self) -> None:
        """Post small and big blinds at the start of a hand."""
        sb_index, bb_index = self._blind_positions()
        self._post_blind(self.players[sb_index], self.small_blind, "малый блайнд")
        self._post_blind(self.players[bb_index], self.big_blind, "большой блайнд")
        self.current_bet = max(self.players[sb_index].current_bet, self.players[bb_index].current_bet)
        for player in self.players:
            if player.chips > 0 and not player.folded:
                player.has_acted = False

    def _post_blind(self, player: Player, amount: int, label: str) -> None:
        """Take blind chips from a player."""
        posted = player.bet(amount)
        player.has_acted = False
        player.last_action = label
        self._log(f"{player.name} ставит {label}: {posted}.")

    def _blind_positions(self) -> Tuple[int, int]:
        """Return small blind and big blind player indexes."""
        active_count = len([player for player in self.players if player.chips > 0])
        if active_count == 2:
            sb = self.dealer_position
            bb = self._next_index_with_chips(sb)
            return sb, bb

        sb = self._next_index_with_chips(self.dealer_position)
        bb = self._next_index_with_chips(sb)
        return sb, bb

    def _first_to_act_preflop(self) -> int:
        """Return first player to act before the flop."""
        _, bb = self._blind_positions()
        return self._next_index_with_chips(bb)

    def _first_to_act_postflop(self) -> int:
        """Return first player to act after community cards are opened."""
        return self._next_index_with_chips(self.dealer_position)

    def _move_to_next_actor(self) -> None:
        """Move turn to the next player who can act."""
        start = self.current_player_index
        index = start
        for _ in range(len(self.players)):
            index = (index + 1) % len(self.players)
            player = self.players[index]
            if player.can_act:
                self.current_player_index = index
                return

    def _skip_to_next_player_if_needed(self) -> None:
        """Skip players who cannot act."""
        for _ in range(len(self.players)):
            if self.active_player.can_act:
                return
            self.current_player_index = (self.current_player_index + 1) % len(self.players)

    def _betting_round_finished(self) -> bool:
        """Return True if the current betting round is complete."""
        actors = [player for player in self.players if player.can_act and not player.folded]
        if not actors:
            return True

        for player in actors:
            if player.current_bet != self.current_bet:
                return False
            if not player.has_acted:
                return False
        return True

    def _advance_stage(self) -> None:
        """Open community cards or finish the hand at showdown."""
        if self._only_one_player_not_folded():
            self._finish_by_fold()
            return

        if self._all_remaining_players_are_all_in():
            self._deal_remaining_board()
            self._showdown()
            return

        if self.stage == "preflop":
            self.community_cards.extend(self.dealer.deal_flop())
            self.stage = "flop"
            self._log("Открыт флоп.")
        elif self.stage == "flop":
            self.community_cards.extend(self.dealer.deal_turn_or_river())
            self.stage = "turn"
            self._log("Открыт терн.")
        elif self.stage == "turn":
            self.community_cards.extend(self.dealer.deal_turn_or_river())
            self.stage = "river"
            self._log("Открыт ривер.")
        elif self.stage == "river":
            self._showdown()
            return

        self._reset_street_bets()
        self.current_player_index = self._first_to_act_postflop()
        self._skip_to_next_player_if_needed()

    def _reset_street_bets(self) -> None:
        """Reset all current street bets."""
        self.current_bet = 0
        self.min_raise = self.big_blind
        for player in self.players:
            if not player.folded and not player.all_in:
                player.reset_for_street()

    def _deal_remaining_board(self) -> None:
        """Deal all remaining community cards for all-in showdown."""
        while len(self.community_cards) < 5:
            if len(self.community_cards) == 0:
                self.community_cards.extend(self.dealer.deal_flop())
                self._log("Открыт флоп.")
            else:
                self.community_cards.extend(self.dealer.deal_turn_or_river())
                self._log("Открыта следующая общая карта.")
        self.stage = "river"

    def _showdown(self) -> None:
        """Evaluate hands, split pots and finish the current hand."""
        self.stage = "showdown"
        contenders = [player for player in self.players if not player.folded and player.total_contribution > 0]
        self.showdown_results = {
            player: HandEvaluator.evaluate(player.hand + self.community_cards)
            for player in contenders
        }
        self.awards = self._calculate_side_pots_and_awards()
        for award in self.awards:
            share, remainder = divmod(award.amount, len(award.winners))
            for index, winner in enumerate(award.winners):
                winner.chips += share + (1 if index < remainder else 0)

            winner_names = ", ".join(winner.name for winner in award.winners)
            hand_name = award.hand_result.name if award.hand_result else "без вскрытия"
            self._log(f"Банк {award.amount} получает: {winner_names}. Комбинация: {hand_name}.")

        self.stage = "hand_over"
        self._check_game_over_after_hand()

    def _finish_by_fold(self) -> None:
        """Award the pot to the only player who did not fold."""
        winner = next(player for player in self.players if not player.folded and player.total_contribution > 0)
        amount = self.pot
        winner.chips += amount
        self.awards = [PotAward(amount, [winner], None)]
        self._log(f"{winner.name} выигрывает банк {amount}: остальные сбросили карты.")
        self.stage = "hand_over"
        self._check_game_over_after_hand()

    def _calculate_side_pots_and_awards(self) -> List[PotAward]:
        """Calculate main and side pots for all-in situations."""
        contributions = {player: player.total_contribution for player in self.players if player.total_contribution > 0}
        levels = sorted(set(contributions.values()))
        previous = 0
        awards: List[PotAward] = []

        for level in levels:
            pot_amount = sum(min(level, amount) - previous for amount in contributions.values() if amount > previous)
            if pot_amount <= 0:
                previous = level
                continue

            eligible = [
                player for player, amount in contributions.items()
                if amount >= level and not player.folded
            ]
            if not eligible:
                previous = level
                continue

            best_result = max(self.showdown_results[player] for player in eligible)
            winners = [player for player in eligible if self.showdown_results[player] == best_result]
            awards.append(PotAward(pot_amount, winners, best_result))
            previous = level

        return awards

    def _only_one_player_not_folded(self) -> bool:
        """Return True if only one participant has not folded."""
        return len([player for player in self.players if not player.folded and player.total_contribution > 0]) == 1

    def _all_remaining_players_are_all_in(self) -> bool:
        """Return True if no remaining player can make additional decisions."""
        remaining = [player for player in self.players if not player.folded and player.total_contribution > 0]
        return bool(remaining) and all(not player.can_act for player in remaining)

    def _mark_others_need_action(self, raiser: Player) -> None:
        """After a raise, mark all other active players as needing action."""
        for player in self.players:
            if player is not raiser and player.can_act:
                player.has_acted = False
        raiser.has_acted = True

    def _next_index_with_chips(self, start_index: int) -> int:
        """Return next player index clockwise with chips."""
        if not any(player.chips > 0 for player in self.players):
            return 0

        index = start_index
        for _ in range(len(self.players)):
            index = (index + 1) % len(self.players)
            if self.players[index].chips > 0:
                return index
        return 0

    def _remove_empty_players_from_hand(self) -> None:
        """Mark players with zero chips as folded for the next hand."""
        for player in self.players:
            if player.chips <= 0:
                player.folded = True

    def _single_remaining_stack_player(self) -> Optional[Player]:
        """Return the winner if only one player still has chips."""
        alive = [player for player in self.players if player.chips > 0]
        if len(alive) == 1:
            return alive[0]
        return None

    def _check_game_over_after_hand(self) -> None:
        """Check if the whole game has ended after a hand."""
        winner = self._single_remaining_stack_player()
        if winner:
            self.game_winner = winner
            self.stage = "game_over"
            self._log(f"Игра окончена. Победитель: {winner.name}.")

    def _log(self, message: str) -> None:
        """Add a message to the table log."""
        self.message_log.append(message)
        if len(self.message_log) > 8:
            self.message_log = self.message_log[-8:]
