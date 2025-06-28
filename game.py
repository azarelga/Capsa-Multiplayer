import random
import sys
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

def show_session_menu():
    print("\n" + "=" * 50)
    print("CAPSA MULTIPLAYER - SESSION SELECTION")
    print("=" * 50)
    print("1. Buat session baru")
    print("2. Join session yang sudah ada")
    print("3. Keluar")
    print("=" * 50)

    while True:
        try:
            choice = input("Pilih opsi (1-3): ").strip()
            if choice in ["1", "2", "3"]:
                return int(choice)
            else:
                print("Pilihan tidak valid. Ketik 1, 2, atau 3.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)


def get_session_name():
    while True:
        session_name = input("Masukkan nama session: ").strip()
        if session_name:
            return session_name
        else:
            print("Nama session tidak boleh kosong.")


def get_creator_name():
    while True:
        creator_name = input("Masukkan nama Anda: ").strip()
        if creator_name:
            return creator_name
        else:
            print("Nama tidak boleh kosong.")


def get_player_name():
    while True:
        player_name = input("Masukkan nama Anda: ").strip()
        if player_name:
            return player_name
        else:
            print("Nama tidak boleh kosong.")


def show_sessions_list(sessions):
    if not sessions:
        print("\nTidak ada session yang tersedia.")
        return None

    print("\nDAFTAR SESSION YANG TERSEDIA:")
    print("-" * 70)
    print(
        f"{'No':<3} {'Nama Session':<20} {'Creator':<15} {'Players':<8} {'Dibuat':<15}"
    )
    print("-" * 70)

    for i, session in enumerate(sessions, 1):
        print(
            f"{i:<3} {session['session_name']:<20} {session['creator_name']:<15} "
            f"{session['player_count']}/4{'':<3} {session['created_at']:<15}"
        )

    print("-" * 70)

    while True:
        try:
            choice = input(
                f"Pilih session (1-{len(sessions)}) atau 0 untuk kembali: "
            ).strip()
            if choice == "0":
                return None

            choice_num = int(choice)
            if 1 <= choice_num <= len(sessions):
                return sessions[choice_num - 1]["session_id"]
            else:
                print(f"Pilihan tidak valid. Ketik 1-{len(sessions)} atau 0.")
        except ValueError:
            print("Masukkan angka yang valid.")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)

def init_pygame():
    pygame.init()

    WIDTH, HEIGHT = 1200, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Capsa Multiplayer HTTP")

    clock = pygame.time.Clock()
    FPS = 60

    return screen, clock, WIDTH, HEIGHT, FPS

def deal(some_players):
    n = len(some_players)
    random.shuffle(deck)
    for i in range(0, n):
        some_players[i].hand = sorted(
            deck[int(i * (52 / n)) : int((i + 1) * (52 / n))],
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
                    (v[0] == v[1]) and (v[3] == v[4]) and (v[2] == v[1] or v[2] == v[3])
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

def draw_game(screen, client, WIDTH, HEIGHT):
    screen.fill(DARK_GREEN)
    
    # Draw table background seperti di game.py
    table_rect = pygame.Rect(
        WIDTH // 6, HEIGHT // 4, 2 * WIDTH // 3, HEIGHT // 2
    )
    pygame.draw.ellipse(screen, GREEN, table_rect)
    pygame.draw.ellipse(screen, BLACK, table_rect, 3)
    
    font_large = pygame.font.Font(None, 36)
    font_medium = pygame.font.Font(None, 24)
    font_small = pygame.font.Font(None, 20)
    
    if not client.connected:
        error_text = font_large.render("DISCONNECTED", True, RED)
        screen.blit(error_text, (WIDTH//2 - 100, HEIGHT//2))
        return [], []
    
    # Title with session info
    title = font_large.render(f"CAPSA MULTIPLAYER - {client.session_name}", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 10))
    
    # Player info with custom names
    if client.player_name:
        player_text = font_medium.render(f"You: {client.player_name}", True, SELECTED_COLOR)
        screen.blit(player_text, (10, 50))
    
    # Current player with custom names
    current_text = font_medium.render(f"Turn: {client.game_data['current_player_name']}", True, WHITE)
    screen.blit(current_text, (10, 80))
    
    # Players info with custom names and better formatting
    y_pos = 120
    title_players = font_medium.render("Players:", True, WHITE)
    screen.blit(title_players, (10, y_pos))
    y_pos += 30
    
    # Get list of players who passed this round
    players_passed = client.game_data.get('players_passed', [])
    
    for i, name in enumerate(client.game_data['players_names']):
        if name:
            count = client.game_data['players_card_counts'][i] if i < len(client.game_data['players_card_counts']) else 0
            
            # Determine color and prefix based on player status
            if i in players_passed:
                # Player has passed - show in grey/dim color
                color = GREY
                prefix = "X "  # X to indicate passed
                status_suffix = " (PASSED)"
            elif i == client.game_data['current_player_index']:
                color = HIGHLIGHT_COLOR  # Bright yellow for current player
                prefix = "> "
                status_suffix = ""
            elif i == client.player_index:
                color = SELECTED_COLOR  # Cyan for yourself
                prefix = "* "
                status_suffix = ""
            else:
                color = WHITE
                prefix = "  "
                status_suffix = ""
            
            # Show slot number, custom name, and pass status
            text = font_small.render(f"{prefix}Slot {i+1}: {name} ({count} cards){status_suffix}", True, color)
            screen.blit(text, (15, y_pos))
            y_pos += 25
    
    # Draw played cards in center menggunakan pygame_cards
    if client.game_data['played_cards']:
        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        
        played_cards = [CapsaClientCard(card_data) for card_data in client.game_data['played_cards']]
        start_x = center_x - (len(played_cards) * (CARD_WIDTH + 5) // 2)
        
        for i, card in enumerate(played_cards):
            x = start_x + i * (CARD_WIDTH + 5)
            y = center_y - CARD_HEIGHT // 2
            card.display(screen, x, y)
    
    # Draw my hand menggunakan pygame_cards seperti di game.py
    card_rects = []
    if client.game_data['my_hand']:
        # Store both the card object and original data together
        my_cards_data = client.game_data['my_hand']
        my_cards = [CapsaClientCard(card_data) for card_data in my_cards_data]
        
        start_x = 50
        start_y = HEIGHT - CARD_HEIGHT - 50
        card_spacing = min(50, (WIDTH - 100) // len(my_cards))
        
        temp_card = []
        for i, (card, card_data) in enumerate(zip(my_cards, my_cards_data)):
            x = start_x + i * card_spacing
            selected = card.number in [c['number'] for c in client.selected_cards]
            y = start_y - (30 if selected else 0)  # Raise selected cards more
            
            rect = card.display(screen, x, y, selected)
            temp_card.append((rect, card_data))  # Use the paired original data
        card_rects = temp_card[::-1]
    
    # Draw buttons
    button_rects = []
    if (client.game_data['game_active'] and 
        client.player_index == client.game_data['current_player_index']):
        
        # Play button
        play_rect = pygame.Rect(WIDTH - 200, HEIGHT - 100, 80, 40)
        pygame.draw.rect(screen, GREEN, play_rect)
        pygame.draw.rect(screen, BLACK, play_rect, 2)
        play_text = font_medium.render("PLAY", True, WHITE)
        screen.blit(play_text, (play_rect.x + 20, play_rect.y + 12))
        button_rects.append(('PLAY', play_rect))
        
        # Pass button
        pass_rect = pygame.Rect(WIDTH - 110, HEIGHT - 100, 80, 40)
        pygame.draw.rect(screen, RED, pass_rect)
        pygame.draw.rect(screen, BLACK, pass_rect, 2)
        pass_text = font_medium.render("PASS", True, WHITE)
        screen.blit(pass_text, (pass_rect.x + 20, pass_rect.y + 12))
        button_rects.append(('PASS', pass_rect))
    
    # Start game button
    if not client.game_data['game_active']:
        start_rect = pygame.Rect(WIDTH//2 - 60, HEIGHT - 60, 120, 40)
        pygame.draw.rect(screen, BLUE, start_rect)
        pygame.draw.rect(screen, BLACK, start_rect, 2)
        start_text = font_medium.render("START GAME", True, WHITE)
        screen.blit(start_text, (start_rect.x + 10, start_rect.y + 12))
        button_rects.append(('START', start_rect))
    
    # Draw message
    if client.message and client.message_timer > 0:
        msg_text = font_medium.render(client.message, True, WHITE)
        msg_rect = msg_text.get_rect(center=(WIDTH//2, 100))
        pygame.draw.rect(screen, BLACK, msg_rect.inflate(20, 10))
        pygame.draw.rect(screen, WHITE, msg_rect.inflate(20, 10), 2)
        screen.blit(msg_text, msg_rect)
        client.message_timer -= 1
    
    # Show selected cards count
    if client.selected_cards:
        selected_text = font_medium.render(f"Selected: {len(client.selected_cards)} cards", True, SELECTED_COLOR)
        screen.blit(selected_text, (WIDTH - 300, HEIGHT - 150))
    
    # Show pass status summary if players have passed
    if players_passed and client.game_data['game_active']:
        pass_count = len(players_passed)
        pass_summary = font_small.render(f"{pass_count} player(s) passed this round", True, GREY)
        screen.blit(pass_summary, (WIDTH - 250, HEIGHT - 200))
    
    return card_rects, button_rects

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
HIGHLIGHT_COLOR = (255, 255, 0)
SELECTED_COLOR = (0, 255, 255)

# Initialize deck
deck = []
for i in range(52):
    deck.append(Card(i))