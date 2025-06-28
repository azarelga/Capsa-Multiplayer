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