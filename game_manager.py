"""Game manager and Pygame event loop."""

from __future__ import annotations

import pygame

from constants import BOT_ACTION_DELAY_MS, FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from player import HumanPlayer
from poker_game import PokerGame
from renderer import Renderer
from ui import Button


class GameManager:
    """Coordinate screens, events and the main application loop."""

    def __init__(self) -> None:
        """Initialize Pygame, the window and the first screen."""
        pygame.init()
        pygame.display.set_caption("Texas Hold'em Poker — OOP coursework")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN | pygame.SCALED)
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)

        self.running = True
        self.state = "menu"
        self.player_count = 2
        self.menu_error = ""
        self.game: PokerGame | None = None
        self.last_bot_action_time = 0

        self.minus_button = Button(pygame.Rect(470, 302, 56, 38), "-")
        self.plus_button = Button(pygame.Rect(574, 302, 56, 38), "+")
        self.chip_buttons = [
            Button(pygame.Rect(395, 475, 85, 38), "1000"),
            Button(pygame.Rect(508, 475, 85, 38), "2000"),
            Button(pygame.Rect(621, 475, 85, 38), "5000"),
        ]
        self.start_button = Button(pygame.Rect(455, 605, 190, 48), "Начать игру")

    def run(self) -> None:
        """Run the main application loop until the user exits."""
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(FPS)

        pygame.quit()

    def _handle_events(self) -> None:
        """Dispatch Pygame events according to the current state."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
                return

            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "game":
                self._handle_game_event(event)

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        """Process start-screen events."""
        self.renderer.chips_input.handle_event(event)

        if self.minus_button.handle_event(event):
            self.player_count = max(2, self.player_count - 1)

        if self.plus_button.handle_event(event):
            self.player_count = min(6, self.player_count + 1)

        for button in self.chip_buttons:
            if button.handle_event(event):
                self.renderer.chips_input.text = button.text

        if self.start_button.handle_event(event):
            self._start_game()

    def _handle_game_event(self, event: pygame.event.Event) -> None:
        """Process events on the game screen."""
        if not self.game:
            return

        self.renderer.bet_input.handle_event(event)

        if self.game.stage == "hand_over":
            if self.renderer.next_hand_button.handle_event(event):
                self.game.start_new_hand()
            return

        if self.game.stage == "game_over":
            if self.renderer.new_game_button.handle_event(event):
                self._return_to_menu()
            return

        if not isinstance(self.game.active_player, HumanPlayer):
            return

        if self.renderer.action_buttons["check"].handle_event(event):
            self.game.handle_human_action("check")
        elif self.renderer.action_buttons["call"].handle_event(event):
            self.game.handle_human_action("call")
        elif self.renderer.action_buttons["bet"].handle_event(event):
            self.game.handle_human_action("bet", self.renderer.bet_input.value(40))
        elif self.renderer.action_buttons["all_in"].handle_event(event):
            self.game.handle_human_action("all_in")
        elif self.renderer.action_buttons["fold"].handle_event(event):
            self.game.handle_human_action("fold")

    def _update(self) -> None:
        """Update bot turns and other time-dependent logic."""
        if self.state != "game" or not self.game:
            return

        if self.game.stage in PokerGame.STAGES and not isinstance(self.game.active_player, HumanPlayer):
            now = pygame.time.get_ticks()
            if now - self.last_bot_action_time >= BOT_ACTION_DELAY_MS:
                self.game.process_bot_turn()
                self.last_bot_action_time = now

    def _draw(self) -> None:
        """Draw the current frame and flip the display."""
        if self.state == "menu":
            self.renderer.draw_menu(self.player_count, self.menu_error)
            self.minus_button.draw(self.screen, self.renderer.font)
            self.plus_button.draw(self.screen, self.renderer.font)
            for button in self.chip_buttons:
                button.draw(self.screen, self.renderer.font)
            self.start_button.draw(self.screen, self.renderer.font)
        elif self.state == "game" and self.game:
            self.renderer.draw_game(self.game)

        pygame.display.flip()

    def _start_game(self) -> None:
        """Create a new PokerGame from menu parameters."""
        chips = self.renderer.chips_input.value(0)
        if chips < 100:
            self.menu_error = "Введите начальное количество фишек не меньше 100."
            return

        try:
            self.game = PokerGame(self.player_count, chips)
        except ValueError as error:
            self.menu_error = str(error)
            return

        self.menu_error = ""
        self.state = "game"
        self.last_bot_action_time = pygame.time.get_ticks()

    def _return_to_menu(self) -> None:
        """Return to the start screen and discard the current game."""
        self.game = None
        self.state = "menu"
        self.menu_error = ""
