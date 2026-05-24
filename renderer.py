"""Pygame renderer for the Texas Hold'em project."""

from __future__ import annotations

import math
import os
from typing import Dict, List, Tuple

import pygame

from card import Card
from constants import (
    BLACK,
    BLUE,
    CARD_BACK,
    CARD_BORDER,
    CARD_GAP,
    CARD_HEIGHT,
    CARD_WIDTH,
    DARK_GREEN,
    ERROR_RED,
    FELT_LINE,
    GOLD,
    GRAY,
    LIGHT_GRAY,
    RED,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TABLE_GREEN,
    WHITE,
)
from player import HumanPlayer, Player
from poker_game import PokerGame
from ui import Button, TextInput


class Renderer:
    """Draw all game screens and reusable visual elements."""

    def __init__(self, screen: pygame.Surface) -> None:
        """Initialize renderer, fonts, static UI widgets and image assets."""
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 21)
        self.small_font = pygame.font.SysFont("arial", 17)
        self.tiny_font = pygame.font.SysFont("arial", 14)
        self.big_font = pygame.font.SysFont("arial", 34, bold=True)
        self.title_font = pygame.font.SysFont("arial", 48, bold=True)
        self.card_font = pygame.font.SysFont("arial", 24, bold=True)
        self.log_font = pygame.font.SysFont("arial", 16)

        self.bet_input = TextInput(pygame.Rect(920, 638, 95, 38), "40")
        self.chips_input = TextInput(pygame.Rect(485, 390, 130, 42), "1000")

        self.action_buttons: Dict[str, Button] = {
            "check": Button(pygame.Rect(410, 638, 90, 38), "Чек"),
            "call": Button(pygame.Rect(510, 638, 90, 38), "Колл"),
            "bet": Button(pygame.Rect(610, 638, 90, 38), "Бет"),
            "all_in": Button(pygame.Rect(710, 638, 90, 38), "Олл-ин"),
            "fold": Button(pygame.Rect(810, 638, 90, 38), "Фолд"),
        }
        self.next_hand_button = Button(pygame.Rect(460, 636, 190, 45), "Следующая раздача")
        self.new_game_button = Button(pygame.Rect(455, 520, 190, 48), "Новая игра")

        self.assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        self.cards_dir = os.path.join(self.assets_dir, "cards")
        self.table_image = self._safe_load_image("table.png")
        self.card_back_image = self._safe_load_image("card_back.png", (CARD_WIDTH, CARD_HEIGHT))
        self.card_images = self._load_card_images()

    def draw_menu(self, player_count: int, error_message: str = "") -> None:
        """Draw the start screen."""
        self._draw_fullscreen_background()
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 24, 12, 135))
        self.screen.blit(overlay, (0, 0))

        self._draw_decorative_menu_cards()
        self._draw_centered_text_with_shadow("Техасский холдем-покер", self.title_font, WHITE, 128)

        panel = pygame.Rect(350, 210, 400, 365)
        self._draw_translucent_panel(panel, (22, 83, 52, 222), FELT_LINE, 18, 3)

        self._draw_centered_text_at("Настройки игры", self.big_font, GOLD, panel.centerx, 248)
        self._draw_centered_text_at("Количество игроков", self.font, WHITE, panel.centerx, 292)
        self._draw_centered_text_at(str(player_count), self.big_font, GOLD, panel.centerx, 324)

        self._draw_centered_text_at("Начальные фишки", self.font, WHITE, panel.centerx, 372)
        self.chips_input.draw(self.screen, self.font, "1000")

        self._draw_centered_text_at("Быстрый выбор фишек", self.small_font, LIGHT_GRAY, panel.centerx, 452)
        self._draw_centered_text_at("Допустимо: 2–6 игроков, фишки от 100", self.small_font, LIGHT_GRAY, panel.centerx, 535)

        if error_message:
            self._draw_centered_text_at(error_message, self.small_font, ERROR_RED, panel.centerx, 560)

    def draw_game(self, game: PokerGame) -> None:
        """Draw a complete in-game frame."""
        self.screen.fill((13, 80, 43))
        self._draw_table()
        self._draw_table_vignette()
        self._draw_community_cards(game.community_cards)
        self._draw_pot_and_stage(game)
        self._draw_players(game)
        self._draw_messages(game.message_log)

        if game.stage in PokerGame.STAGES and isinstance(game.active_player, HumanPlayer):
            self._draw_action_panel(game)
        elif game.stage == "hand_over":
            self._draw_hand_over_panel(game)
        elif game.stage == "game_over":
            self._draw_game_over(game)

    def draw_button(self, button: Button) -> None:
        """Draw one button with the default font."""
        button.draw(self.screen, self.font)

    def _safe_load_image(self, name: str, size: Tuple[int, int] | None = None) -> pygame.Surface | None:
        """Load one image from the assets directory and optionally scale it."""
        path = os.path.join(self.assets_dir, name)
        if not os.path.exists(path):
            print(f"[WARNING] Файл не найден: {path}")
            return None
        try:
            image = pygame.image.load(path).convert_alpha()
        except pygame.error as error:
            print(f"[WARNING] Не удалось загрузить изображение: {path}")
            print(f"[WARNING] Причина: {error}")
            return None
        if size:
            image = pygame.transform.smoothscale(image, size)
        return image

    def _load_card_images(self) -> Dict[str, pygame.Surface]:
        """Load card face images and put a white background under transparent PNGs."""
        images: Dict[str, pygame.Surface] = {}
        if not os.path.isdir(self.cards_dir):
            return images

        allowed_extensions = (".png", ".jpg", ".jpeg", ".bmp")
        for file_name in os.listdir(self.cards_dir):
            if not file_name.lower().endswith(allowed_extensions):
                continue
            key = os.path.splitext(file_name)[0].lower()
            path = os.path.join(self.cards_dir, file_name)
            try:
                image = pygame.image.load(path).convert_alpha()
                background = pygame.Surface(image.get_size(), pygame.SRCALPHA)
                background.fill((255, 255, 255, 255))
                background.blit(image, (0, 0))
                images[key] = pygame.transform.smoothscale(background, (CARD_WIDTH, CARD_HEIGHT))
            except pygame.error as error:
                print(f"[WARNING] Не удалось загрузить изображение карты: {path}")
                print(f"[WARNING] Причина: {error}")
        return images

    def _draw_fullscreen_background(self) -> None:
        """Draw the table image as a fullscreen cover background."""
        if not self.table_image:
            self.screen.fill(DARK_GREEN)
            return

        screen_rect = self.screen.get_rect()
        image_rect = self.table_image.get_rect()
        scale = max(screen_rect.width / image_rect.width, screen_rect.height / image_rect.height)
        new_size = (int(image_rect.width * scale), int(image_rect.height * scale))
        scaled = pygame.transform.smoothscale(self.table_image, new_size)
        scaled_rect = scaled.get_rect(center=screen_rect.center)
        self.screen.blit(scaled, scaled_rect)

    def _draw_table(self) -> None:
        """Draw the poker table background."""
        self._draw_fullscreen_background()

    def _draw_table_vignette(self) -> None:
        """Draw a soft transparent overlay to improve text readability."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (0, 0, 0, 45), pygame.Rect(0, 0, SCREEN_WIDTH, 100))
        pygame.draw.rect(overlay, (0, 0, 0, 55), pygame.Rect(0, 560, SCREEN_WIDTH, 160))
        self.screen.blit(overlay, (0, 0))

    def _draw_community_cards(self, cards: List[Card]) -> None:
        """Draw community cards in the center of the table."""
        total_width = 5 * CARD_WIDTH + 4 * CARD_GAP
        start_x = SCREEN_WIDTH // 2 - total_width // 2
        y = 305
        row_rect = pygame.Rect(start_x - 18, y - 15, total_width + 36, CARD_HEIGHT + 30)
        self._draw_translucent_panel(row_rect, (0, 68, 32, 90), (255, 255, 255, 80), 18, 1)

        for index in range(5):
            x = start_x + index * (CARD_WIDTH + CARD_GAP)
            if index < len(cards):
                self._draw_card(cards[index], x, y)
            else:
                self._draw_empty_card(x, y)

    def _draw_players(self, game: PokerGame) -> None:
        """Draw all player panels and their private cards."""
        positions = self._player_positions(len(game.players))
        for index, player in enumerate(game.players):
            x, y = positions[index]
            active = game.stage in PokerGame.STAGES and index == game.current_player_index
            dealer = index == game.dealer_position
            reveal_cards = isinstance(player, HumanPlayer) or game.stage in {"showdown", "hand_over", "game_over"}

            self._draw_player_panel(player, x, y, active, dealer)
            self._draw_hole_cards(player, x, y, reveal_cards)

            if active:
                self._draw_active_pointer(x, y)

            if player in game.showdown_results:
                result = game.showdown_results[player]
                self._draw_centered_text_at(result.name, self.small_font, GOLD, x, y + 74)

    def _player_positions(self, count: int) -> List[Tuple[int, int]]:
        """Return screen positions for players around the table."""
        bottom = 535
        if count == 2:
            return [(SCREEN_WIDTH // 2, bottom), (SCREEN_WIDTH // 2, 95)]
        if count == 3:
            return [(SCREEN_WIDTH // 2, bottom), (190, 250), (910, 250)]
        if count == 4:
            return [(SCREEN_WIDTH // 2, bottom), (165, 330), (SCREEN_WIDTH // 2, 95), (935, 330)]
        if count == 5:
            return [(SCREEN_WIDTH // 2, bottom), (160, 390), (245, 155), (855, 155), (940, 390)]
        return [(SCREEN_WIDTH // 2, bottom), (155, 395), (180, 175), (SCREEN_WIDTH // 2, 95), (920, 175), (945, 395)]

    def _draw_player_panel(self, player: Player, x: int, y: int, active: bool, dealer: bool) -> None:
        """Draw player information panel."""
        rect = pygame.Rect(x - 86, y - 49, 172, 94)
        if active:
            pulse = (math.sin(pygame.time.get_ticks() / 220) + 1) / 2
            glow_radius = int(18 + pulse * 7)
            self._draw_glow(rect.inflate(glow_radius, glow_radius), GOLD, 42)

        fill = (43, 112, 72, 220) if not active else (58, 139, 82, 235)
        border = GOLD if active else (238, 238, 225)
        self._draw_translucent_panel(rect, fill, border, 14, 2)

        name_color = GRAY if player.chips <= 0 else WHITE
        self._draw_centered_text_at(player.name, self.font, name_color, x, y - 35)
        self._draw_centered_text_at(f"Фишки: {player.chips}", self.small_font, LIGHT_GRAY, x, y - 13)
        self._draw_centered_text_at(f"Ставка: {player.current_bet}", self.small_font, LIGHT_GRAY, x, y + 8)

        if player.folded:
            self._draw_centered_text_at("FOLD", self.small_font, ERROR_RED, x, y + 30)
        elif player.all_in:
            self._draw_centered_text_at("ALL-IN", self.small_font, GOLD, x, y + 30)
        elif player.last_action:
            self._draw_centered_text_at(player.last_action, self.small_font, GOLD, x, y + 30)

        if dealer:
            pygame.draw.circle(self.screen, (35, 35, 35), (x + 96, y - 31), 17)
            pygame.draw.circle(self.screen, WHITE, (x + 94, y - 34), 16)
            pygame.draw.circle(self.screen, GOLD, (x + 94, y - 34), 16, width=2)
            self._draw_centered_text_at("D", self.small_font, BLACK, x + 94, y - 34)

    def _draw_hole_cards(self, player: Player, x: int, y: int, reveal: bool) -> None:
        """Draw player's private cards."""
        card_y = y + 47 if y < SCREEN_HEIGHT // 2 else y - 144
        start_x = x - CARD_WIDTH - 4
        for index in range(2):
            card_x = start_x + index * (CARD_WIDTH + 8)
            if index >= len(player.hand):
                continue
            if player.folded and not reveal:
                self._draw_card_back(card_x, card_y)
            elif reveal:
                self._draw_card(player.hand[index], card_x, card_y)
            else:
                self._draw_card_back(card_x, card_y)

    def _draw_card(self, card: Card, x: int, y: int) -> None:
        """Draw a face-up card from loaded images or fall back to primitives."""
        self._draw_card_shadow(x, y)
        key = card.image_key()
        image = self.card_images.get(key)
        if image:
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            pygame.draw.rect(self.screen, WHITE, rect, border_radius=8)
            pygame.draw.rect(self.screen, CARD_BORDER, rect, width=2, border_radius=8)
            self.screen.blit(image, (x, y))
            return

        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(self.screen, WHITE, rect, border_radius=8)
        pygame.draw.rect(self.screen, CARD_BORDER, rect, width=2, border_radius=8)

        color = RED if card.is_red else BLACK
        self._draw_text(card.label, x + 8, y + 8, color, self.card_font)
        self._draw_centered_text_at(card.symbol, self.big_font, color, x + CARD_WIDTH // 2, y + CARD_HEIGHT // 2 + 7)
        self._draw_text(card.label, x + CARD_WIDTH - 29, y + CARD_HEIGHT - 34, color, self.card_font)

    def _draw_card_back(self, x: int, y: int) -> None:
        """Draw a face-down card."""
        self._draw_card_shadow(x, y)
        if self.card_back_image:
            self.screen.blit(self.card_back_image, (x, y))
            return

        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(self.screen, CARD_BACK, rect, border_radius=8)
        pygame.draw.rect(self.screen, WHITE, rect, width=2, border_radius=8)
        inner = rect.inflate(-18, -18)
        pygame.draw.rect(self.screen, BLUE, inner, border_radius=5)
        pygame.draw.line(self.screen, WHITE, (x + 16, y + 16), (x + CARD_WIDTH - 16, y + CARD_HEIGHT - 16), 2)
        pygame.draw.line(self.screen, WHITE, (x + CARD_WIDTH - 16, y + 16), (x + 16, y + CARD_HEIGHT - 16), 2)

    def _draw_empty_card(self, x: int, y: int) -> None:
        """Draw an empty community-card placeholder."""
        rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        placeholder = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(placeholder, (255, 255, 255, 24), placeholder.get_rect(), border_radius=8)
        pygame.draw.rect(placeholder, (245, 235, 190, 170), placeholder.get_rect(), width=2, border_radius=8)
        self.screen.blit(placeholder, rect.topleft)

    def _draw_pot_and_stage(self, game: PokerGame) -> None:
        """Draw current stage, blinds and pot information."""
        stage_label = {
            "preflop": "Префлоп",
            "flop": "Флоп",
            "turn": "Терн",
            "river": "Ривер",
            "showdown": "Вскрытие",
            "hand_over": "Конец раздачи",
            "game_over": "Игра окончена",
        }.get(game.stage, game.stage)

        badge = pygame.Rect(SCREEN_WIDTH // 2 - 250, 221, 500, 67)
        self._draw_translucent_panel(badge, (8, 55, 30, 185), (255, 230, 120, 180), 18, 2)
        self._draw_centered_text_at(f"{stage_label} | Банк: {game.pot}", self.big_font, GOLD, SCREEN_WIDTH // 2, 246)
        self._draw_centered_text_at(
            f"Блайнды: {game.small_blind}/{game.big_blind} | Текущая ставка: {game.current_bet}",
            self.small_font,
            WHITE,
            SCREEN_WIDTH // 2,
            278,
        )

    def _draw_messages(self, messages: List[str]) -> None:
        """Draw recent game messages with line wrapping."""
        panel = pygame.Rect(28, SCREEN_HEIGHT - 118, 340, 100)
        self._draw_translucent_panel(panel, (19, 48, 37, 225), (245, 225, 160, 180), 14, 1)
        self._draw_text("Сообщения", panel.x + 14, panel.y + 8, GOLD, self.small_font)

        y = panel.y + 32
        max_width = panel.width - 26
        line_height = 15
        wrapped_lines: List[str] = []
        for message in messages[-5:]:
            wrapped_lines.extend(self._wrap_text(message, self.log_font, max_width))
        for line in wrapped_lines[-4:]:
            self._draw_text(line, panel.x + 14, y, WHITE, self.log_font)
            y += line_height

    def _draw_action_panel(self, game: PokerGame) -> None:
        """Draw action buttons and bet input for the human turn."""
        actions = game.get_available_actions(game.human_player)
        panel = pygame.Rect(392, SCREEN_HEIGHT - 118, 678, 100)
        self._draw_translucent_panel(panel, (15, 54, 38, 215), (255, 230, 120, 120), 16, 1)

        for action, button in self.action_buttons.items():
            button.enabled = bool(actions.get(action, False))
            button.draw(self.screen, self.font)

        self._draw_text("Сумма:", 920, 612, WHITE, self.small_font)
        self.bet_input.draw(self.screen, self.font, "40")
        call_amount = int(actions["call_amount"])
        hint = "Можно чекать" if call_amount == 0 else f"Колл: {call_amount}"
        self._draw_text(hint, 1018, 648, GOLD, self.small_font)

    def _draw_hand_over_panel(self, game: PokerGame) -> None:
        """Draw hand summary panel with winner information."""
        panel = pygame.Rect(350, 585, 400, 110)
        self._draw_translucent_panel(panel, (25, 60, 45, 235), GOLD, 16, 2)

        if game.awards:
            first_award = game.awards[0]
            winners = ", ".join(player.name for player in first_award.winners)
            self._draw_centered_text_at(f"Победитель: {winners}", self.font, GOLD, SCREEN_WIDTH // 2, 610)
            if first_award.hand_result:
                self._draw_centered_text_at(first_award.hand_result.name, self.small_font, WHITE, SCREEN_WIDTH // 2, 635)
        self.next_hand_button.draw(self.screen, self.font)

    def _draw_game_over(self, game: PokerGame) -> None:
        """Draw final game-over screen overlay."""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 165))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(315, 250, 470, 350)
        self._draw_translucent_panel(panel, (27, 88, 55, 245), GOLD, 20, 3)
        self._draw_centered_text_with_shadow("Игра окончена", self.title_font, WHITE, 320)
        winner = game.game_winner.name if game.game_winner else "не определён"
        self._draw_centered_text_at(f"Победитель: {winner}", self.big_font, GOLD, SCREEN_WIDTH // 2, 390)
        self._draw_chip_stack(SCREEN_WIDTH // 2, 455, 500)
        self.new_game_button.draw(self.screen, self.font)

    def _draw_decorative_menu_cards(self) -> None:
        """Draw decorative cards on the start screen."""
        keys = ["a_of_spades", "k_of_hearts", "q_of_diamonds", "j_of_clubs"]
        x_positions = [112, 185, SCREEN_WIDTH - 248, SCREEN_WIDTH - 175]
        for index, key in enumerate(keys):
            image = self.card_images.get(key)
            if not image:
                continue
            scaled = pygame.transform.smoothscale(image, (78, 110))
            angle = [-12, 8, -7, 12][index]
            rotated = pygame.transform.rotate(scaled, angle)
            rect = rotated.get_rect(center=(x_positions[index], 170 + (index % 2) * 18))
            self.screen.blit(rotated, rect)

    def _draw_active_pointer(self, x: int, y: int) -> None:
        """Draw a small animated pointer near the active player."""
        offset = int(3 * math.sin(pygame.time.get_ticks() / 180))
        if y > SCREEN_HEIGHT // 2:
            points = [(x - 12, y - 164 + offset), (x + 12, y - 164 + offset), (x, y - 146 + offset)]
        else:
            points = [(x - 12, y + 160 + offset), (x + 12, y + 160 + offset), (x, y + 142 + offset)]
        pygame.draw.polygon(self.screen, GOLD, points)
        pygame.draw.polygon(self.screen, BLACK, points, width=1)

    def _draw_chip_stack(self, x: int, y: int, amount: int) -> None:
        """Decorative chips are disabled in this UI version."""
        return

    def _draw_card_shadow(self, x: int, y: int) -> None:
        """Draw a soft shadow under a card."""
        shadow = pygame.Surface((CARD_WIDTH + 10, CARD_HEIGHT + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 100), shadow.get_rect(), border_radius=10)
        self.screen.blit(shadow, (x + 4, y + 6))

    def _draw_glow(self, rect: pygame.Rect, color: Tuple[int, int, int], alpha: int) -> None:
        """Draw a soft glow around a rectangle."""
        glow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        rgba = (*color, alpha)
        pygame.draw.rect(glow, rgba, glow.get_rect(), border_radius=22)
        self.screen.blit(glow, rect.topleft)

    def _draw_translucent_panel(
        self,
        rect: pygame.Rect,
        fill: Tuple[int, ...],
        border: Tuple[int, ...],
        radius: int,
        width: int,
    ) -> None:
        """Draw a rounded translucent panel with shadow and border."""
        shadow = pygame.Surface((rect.width + 12, rect.height + 12), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 95), shadow.get_rect(), border_radius=radius + 3)
        self.screen.blit(shadow, (rect.x + 5, rect.y + 6))

        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, fill, panel.get_rect(), border_radius=radius)
        pygame.draw.rect(panel, border, panel.get_rect(), width=width, border_radius=radius)
        self.screen.blit(panel, rect.topleft)

    def _wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """Split text into lines that fit the specified pixel width."""
        words = text.split()
        if not words:
            return [""]

        lines: List[str] = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if font.size(candidate)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _draw_text(self, text: str, x: int, y: int, color: Tuple[int, int, int], font: pygame.font.Font) -> None:
        """Draw text at a fixed position."""
        surface = font.render(text, True, color)
        self.screen.blit(surface, (x, y))

    def _draw_centered_text(self, text: str, font: pygame.font.Font, color: Tuple[int, int, int], y: int) -> None:
        """Draw horizontally centered text."""
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(SCREEN_WIDTH // 2, y))
        self.screen.blit(surface, rect)

    def _draw_centered_text_with_shadow(self, text: str, font: pygame.font.Font, color: Tuple[int, int, int], y: int) -> None:
        """Draw horizontally centered text with a soft shadow."""
        shadow = font.render(text, True, (0, 0, 0))
        shadow_rect = shadow.get_rect(center=(SCREEN_WIDTH // 2 + 3, y + 3))
        self.screen.blit(shadow, shadow_rect)
        self._draw_centered_text(text, font, color, y)

    def _draw_centered_text_at(
        self,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        x: int,
        y: int,
    ) -> None:
        """Draw centered text at an exact point."""
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(x, y))
        self.screen.blit(surface, rect)
