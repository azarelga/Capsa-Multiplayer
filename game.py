import random
from pygame_cards.classics import CardSets
import math
import pygame
from enum import Enum

unordered_set = [
    CardSets.n52[26:39],
    CardSets.n52[39:52],
    CardSets.n52[13:26],
    CardSets.n52[0:13],
]
card_sets = [card for group in unordered_set for card in group]


class GameState(Enum):
    MENU = 1
    PLAYING = 2
    GAME_OVER = 3


class Player:
    def __init__(self, x):
        self.hand = []
        self.foot = []
        self.name = x

    def __repr__(self):
        return self.name

    def opponents(self, people):
        opponents = list(people)
        opponents.remove(self)
        return opponents

    def next_player(self, people):
        return people[(people.index(self) + 1) % len(people)]


class Button:
    def __init__(self, x, y, width, height, text, font_size=24):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font_size = font_size
        self.font = pygame.font.SysFont(None, font_size)
        self.is_hovered = False

    def draw(self, screen):
        color = LIGHT_GREY if self.is_hovered else GREY
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, BLACK, self.rect, 2)

        text_surface = self.font.render(self.text, True, BLACK)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class Text:
    def __init__(self, text, size, colour, background, location):
        self.text = text
        self.size = size
        self.colour = colour
        self.location = location
        self.background = background

    def display(self, screen):
        basic_font = pygame.font.SysFont(None, self.size)
        words = basic_font.render(
            self.text, True, self.colour, self.background)
        screen.blit(words, self.location)


class Card:
    def __init__(self, number):
        self.number = number
        self.suit = number % 4
        self.value = math.floor(number / 4)
        self.selected = False

        if self.value == 12:
            self.pp_value = 2
        elif self.value == 11:
            self.pp_value = "A"
        elif self.value == 10:
            self.pp_value = "K"
        elif self.value == 9:
            self.pp_value = "Q"
        elif self.value == 8:
            self.pp_value = "J"
        else:
            self.pp_value = self.value + 3

        # Use pygame_cards graphics
        big2_value = (self.value + 1) % 13
        self.pygame_card = card_sets[big2_value + 13 * self.suit]
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)

    def display(self, screen, left, top):
        self.rect = pygame.Rect(left, top, CARD_WIDTH, CARD_HEIGHT)

        # Draw card using pygame_cards
        card_image = pygame.transform.scale(
            self.pygame_card.graphics.surface, (CARD_WIDTH, CARD_HEIGHT)
        )
        screen.blit(card_image, (left, top))

        # Highlight if selected
        if self.selected:
            pygame.draw.rect(screen, LIGHT_BLUE, self.rect, 5)


class GameUI:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Big2 Card Game")

        # UI Elements
        self.play_button = Button(width - 120, height - 80, 100, 50, "Play")
        self.pass_button = Button(width - 240, height - 80, 100, 50, "Pass")

        self.selected_cards = []
        self.message = ""
        self.message_timer = 0

    def draw_background(self):
        self.screen.fill(DARK_GREEN)
        # Draw table
        table_rect = pygame.Rect(
            self.width // 6, self.height // 4, 2 * self.width // 3, self.height // 2
        )
        pygame.draw.ellipse(self.screen, GREEN, table_rect)
        pygame.draw.ellipse(self.screen, BLACK, table_rect, 3)

    def draw_player_info(self, current_player, players):
        font = pygame.font.SysFont(None, 24)

        # Current player
        text = f"Current Player: {current_player.name}"
        text_surface = font.render(text, True, WHITE)
        self.screen.blit(text_surface, (10, 10))

        # Other players' card counts
        y_offset = 40
        for player in players:
            if player != current_player:
                text = f"{player.name}: {len(player.hand)} cards"
                text_surface = font.render(text, True, WHITE)
                self.screen.blit(text_surface, (10, y_offset))
                y_offset += 25

    def draw_cards_in_hand(self, cards):
        if not cards:
            return

        start_x = 50
        start_y = self.height - CARD_HEIGHT - 50
        card_spacing = min(50, (self.width - 100) // len(cards))

        for i, card in enumerate(cards):
            x = start_x + i * card_spacing
            y = start_y - (20 if card.selected else 0)
            card.display(self.screen, x, y)

    def draw_played_cards(self, played_cards_history):
        if not played_cards_history:
            return

        center_x = self.width // 2
        center_y = self.height // 2

        # Only show up to the last 5 previous hands in the stack
        max_stack = 5
        stack_history = (
            played_cards_history[-(max_stack + 1): -1]
            if len(played_cards_history) > 1
            else []
        )

        stack_offset = 15  # vertical offset per stack layer
        total = len(stack_history)
        for stack_idx, prev_hand in enumerate(stack_history):
            if prev_hand:
                prev_start_x = center_x - (len(prev_hand) * CARD_WIDTH // 2)
                y_offset = (
                    center_y - CARD_HEIGHT // 2 +
                    stack_offset * (total - stack_idx)
                )
                # Fade older stacks more
                fade = 80 + int(120 * (stack_idx + 1) / (total + 1))
                for i, card in enumerate(prev_hand):
                    card.display(
                        self.screen,
                        prev_start_x + i * (CARD_WIDTH + 5),
                        y_offset,
                    )
                    grey_overlay = pygame.Surface(
                        (CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA
                    )
                    grey_overlay.fill((128, 128, 128, fade))
                    self.screen.blit(
                        grey_overlay,
                        (
                            prev_start_x + i * (CARD_WIDTH + 5),
                            y_offset,
                        ),
                    )

        # Draw current played cards (most recent hand) on top
        current_cards = played_cards_history[-1]
        start_x = center_x - (len(current_cards) * CARD_WIDTH // 2)
        for i, card in enumerate(current_cards):
            card.display(
                self.screen, start_x + i *
                (CARD_WIDTH + 5), center_y - CARD_HEIGHT // 2
            )

    def draw_buttons(self):
        self.play_button.draw(self.screen)
        self.pass_button.draw(self.screen)

    def draw_message(self):
        if self.message and self.message_timer > 0:
            font = pygame.font.SysFont(None, 32)
            text_surface = font.render(self.message, True, WHITE)
            text_rect = text_surface.get_rect(center=(self.width // 2, 100))

            # Draw background for message
            bg_rect = text_rect.inflate(20, 10)
            pygame.draw.rect(self.screen, BLACK, bg_rect)
            pygame.draw.rect(self.screen, WHITE, bg_rect, 2)

            self.screen.blit(text_surface, text_rect)
            self.message_timer -= 1

    def show_message(self, message, duration=180):  # 3 seconds at 60 FPS
        self.message = message
        self.message_timer = duration

    def handle_card_click(self, pos, cards):
        for card in reversed(cards):
            if card.rect.collidepoint(pos):
                card.selected = not card.selected
                if card.selected:
                    if card not in self.selected_cards:
                        self.selected_cards.append(card)
                else:
                    if card in self.selected_cards:
                        self.selected_cards.remove(card)
                return True
        return False


def deal(some_players):
    n = len(some_players)
    random.shuffle(deck)
    for i in range(0, n):
        some_players[i].hand = sorted(
            deck[int(i * (52 / n)): int((i + 1) * (52 / n))],
            key=lambda card: card.number,
        )


def who_starts(some_players):
    for p in some_players:
        if any(card.number == 0 for card in p.hand):
            return p


def value_checker(my_cards, last_cards):
    if len(my_cards) == 0:
        return 0
    elif len(my_cards) == 1:
        if len(last_cards) == 0 or my_cards[0].number > last_cards[0].number:
            return 0
        else:
            return 1
    elif len(my_cards) == 2:
        if my_cards[0].value != my_cards[1].value:
            return 2
        elif len(last_cards) == 0 or my_cards[1].number > last_cards[1].number:
            return 0
        else:
            return 3
    elif len(my_cards) == 3:
        if not (my_cards[0].value == my_cards[1].value == my_cards[2].value):
            return 4
        elif len(last_cards) == 0 or my_cards[2].number > last_cards[2].number:
            return 0
        else:
            return 5
    elif len(my_cards) == 4:
        return 6
    elif len(my_cards) == 5:

        def rank(five_cards):
            if five_cards == []:
                return 0
            else:

                def value(quintuple):
                    va = []
                    for card in quintuple:
                        va.append(card.value - quintuple[0].value)
                    return va

                def suit(quintuple):
                    su = []
                    for card in quintuple:
                        su.append(card.suit)
                    return su

                v = value(five_cards)
                s = suit(five_cards)
                if v == [0, 1, 2, 3, 4]:
                    if s[0] == s[1] == s[2] == s[3] == s[4]:
                        return 5
                    else:
                        return 1
                if s[0] == s[1] == s[2] == s[3] == s[4]:
                    return 2
                elif (
                    (v[0] == v[1]) and (v[3] == v[4]) and (
                        v[2] == v[1] or v[2] == v[3])
                ):
                    return 3
                elif (v[0] == v[1] == v[2] == v[3]) or (v[1] == v[2] == v[3] == v[4]):
                    return 4
                else:
                    return -1

        if rank(my_cards) < rank(last_cards):
            if rank(my_cards) == -1:
                return 7
            else:
                return 8
        if rank(my_cards) > rank(last_cards):
            return 0
        if rank(my_cards) == rank(last_cards):
            if rank(my_cards) == 2 or rank(my_cards) == 5:
                if my_cards[0].suit > last_cards[0].suit:
                    return 0
                elif my_cards[0].suit < last_cards[0].suit:
                    return 9
            if my_cards[4].number > last_cards[4].number:
                return 0
            else:
                return 10


def quantity_checker(my_cards, cards):
    if len(my_cards) == 0 or len(cards) == 0:
        return 0
    elif len(my_cards) > 5:
        return 1
    elif len(my_cards) != len(cards):
        return 2
    else:
        return 0


def play(some_cards, hand, cards):
    if any(card.number == 0 for card in hand) and not any(
        card.number == 0 for card in some_cards
    ):
        return 1
    else:
        if (
            quantity_checker(some_cards, cards) == 0
            and value_checker(some_cards, cards) == 0
        ):
            return 0
        else:
            return 2


def game():
    pygame.init()
    clock = pygame.time.Clock()
    ui = GameUI(WINDOW_WIDTH, WINDOW_HEIGHT)

    # Create players
    players = [Player("Player"), Player("AI 1"),
               Player("AI 2"), Player("AI 3")]

    # Initialize game
    deal(players)
    current_player = who_starts(players)
    played_cards = []  # Current cards on table
    played_cards_history = []  # History of all played hands
    players_passed = set()  # Track who has passed this round

    # Error messages
    error_messages = {
        1: "You must include the 3 of diamonds in your play",
        2: "Invalid hand, try again!",
        3: "You must play a higher pair than the previous play!",
        4: "A three card play must be a three of a kind!",
        5: "You must play a higher three of a kind than the previous play!",
        6: "There is no valid four card play!",
        7: "Invalid hand, try again!",
        8: "You need to play a stronger hand!",
        9: "You need to play a higher suit!",
        10: "You need to play a better hand!",
    }

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle human player input
            if current_player.name == "Player":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if ui.play_button.handle_event(event):
                        selected_cards = ui.selected_cards.copy()
                        if selected_cards:
                            selected_cards.sort(key=lambda card: card.number)
                            result = play(
                                selected_cards, current_player.hand, played_cards
                            )

                            if result == 0:
                                # Valid play
                                for card in selected_cards:
                                    current_player.hand.remove(card)
                                    card.selected = False
                                    card.selected_by = (
                                        current_player.name
                                    )  # Track who played the card
                                played_cards = selected_cards
                                played_cards_history.append(
                                    selected_cards.copy())
                                ui.selected_cards.clear()
                                players_passed.discard(
                                    current_player
                                )  # Remove from passed set

                                if len(current_player.hand) == 0:
                                    ui.show_message(
                                        f"{current_player.name} wins!")
                                    running = False
                                else:
                                    current_player = current_player.next_player(
                                        players)
                                    players_passed.clear()  # Reset passed players after a play
                            else:
                                # Invalid play
                                if result in error_messages:
                                    ui.show_message(error_messages[result])
                                for card in selected_cards:
                                    card.selected = False
                                ui.selected_cards.clear()

                    elif ui.pass_button.handle_event(event):
                        # Pass turn
                        for card in ui.selected_cards:
                            card.selected = False
                        ui.selected_cards.clear()
                        players_passed.add(current_player)
                        ui.show_message(f"{current_player.name} passed.")
                        current_player = current_player.next_player(players)

                        # Check if all other players passed - winner can play anything
                        if len(players_passed) >= len(players) - 1:
                            # The last player who played (the winner) should open the next turn
                            if played_cards_history:
                                current_player = (
                                    players[
                                        [p.name for p in players].index(
                                            played_cards_history[-1][0].selected_by
                                        )
                                    ]
                                    if hasattr(
                                        played_cards_history[-1][0], "selected_by"
                                    )
                                    else current_player
                                )
                                # Skip players who have passed until a new play is made
                                while current_player in players_passed:
                                    current_player = current_player.next_player(
                                        players)
                            played_cards = []  # Reset to allow any combination
                            played_cards_history.clear()  # Clear history for new round
                            players_passed.clear()
                    else:
                        # Handle card selection
                        ui.handle_card_click(event.pos, current_player.hand)

            # Handle button hover effects
            ui.play_button.handle_event(event)
            ui.pass_button.handle_event(event)

        # AI player logic (simplified)
        if current_player.name != "Player" and len(current_player.hand) > 0:
            # Simple AI: play lowest valid card(s) or pass
            pygame.time.wait(1000)  # Delay for AI turn

            # Try to play a single card
            played = False
            for card in current_player.hand:
                if play([card], current_player.hand, played_cards) == 0:
                    current_player.hand.remove(card)
                    played_cards = [card]
                    for c in played_cards:
                        c.selected_by = current_player.name  # Track who played the card
                    played_cards_history.append([card])
                    # Remove from passed set
                    players_passed.discard(current_player)
                    played = True
                    break

            if not played:
                # AI passes
                players_passed.add(current_player)
                ui.show_message(f"{current_player.name} passed.")

            # Check if AI won
            if len(current_player.hand) == 0:
                ui.show_message(f"{current_player.name} wins!")
                running = False
            else:
                current_player = current_player.next_player(players)

            # Skip players who have passed until a new play is made
            while current_player in players_passed:
                current_player = current_player.next_player(players)

            # Check if all players passed except one
            if len(players_passed) >= len(players) - 1:
                played_cards = []  # Reset to allow any combination
                # Set current_player to the last who played
                if played_cards_history:
                    current_player = (
                        players[
                            [p.name for p in players].index(
                                played_cards_history[-1][0].selected_by
                            )
                        ]
                        if hasattr(played_cards_history[-1][0], "selected_by")
                        else current_player
                    )
                played_cards_history.clear()  # Clear history for new round
                players_passed.clear()

        # Draw everything
        ui.draw_background()
        ui.draw_player_info(current_player, players)
        ui.draw_played_cards(played_cards_history)

        if current_player.name == "Player":
            ui.draw_cards_in_hand(current_player.hand)
            ui.draw_buttons()

        ui.draw_message()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


# Constants
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
CARD_WIDTH = 90
CARD_HEIGHT = 120

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 128, 0)
BLUE = (0, 0, 255)
PURPLE = (255, 0, 255)
GREY = (128, 128, 128)
LIGHT_GREY = (200, 200, 200)
DARK_GREEN = (0, 100, 0)
LIGHT_BLUE = (173, 216, 230)

# Initialize deck
deck = []
for i in range(52):
    deck.append(Card(i))

if __name__ == "__main__":
    game()
