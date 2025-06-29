"""
Capsa Multiplayer Game
=====================

A Big Two (Capsa) card game implementation with both TCP and HTTP server/client support.

Available modules:
- common: Shared game logic and base server classes
- tcp: TCP-based implementation
- http: HTTP-based implementation
"""

# Make common modules easily accessible
from .common.game import (
    # Constants
    WINDOW_WIDTH, WINDOW_HEIGHT, CARD_WIDTH, CARD_HEIGHT,
    WHITE, BLACK, RED, GREEN, BLUE, PURPLE, GREY, LIGHT_GREY,
    DARK_GREEN, LIGHT_BLUE, HIGHLIGHT_COLOR, SELECTED_COLOR,

    # Game classes and enums
    GameState, Player, Card, CapsaClientCard,

    # Game functions
    deal, who_starts, value_checker, quantity_checker, play,

    # UI functions
    show_session_menu, get_session_name, get_creator_name,
    get_player_name, show_sessions_list, init_pygame, draw_game,

    # Card deck
    deck, card_sets, unordered_set
)
from .common.server import CapsaGameServer, GameSession, CapsaGameState