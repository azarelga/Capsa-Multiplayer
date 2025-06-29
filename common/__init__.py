"""
Common Game Components
====================

Shared game logic, card handling, and base server classes used by both
TCP and HTTP implementations.

Key Components:
- GameState: Game state enumeration
- Player: Player class with hand management
- Card: Card representation
- Game logic functions: deal, who_starts, play, value_checker, etc.
- CapsaGameServer: Base server class
- GameSession: Session management
"""

# Import all game components
from .game import (
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

from .server import (
    # Server classes
    CapsaGameServer, GameSession, CapsaGameState
)

__all__ = [
    # Game constants
    'WINDOW_WIDTH', 'WINDOW_HEIGHT', 'CARD_WIDTH', 'CARD_HEIGHT',
    'WHITE', 'BLACK', 'RED', 'GREEN', 'BLUE', 'PURPLE', 'GREY',
    'LIGHT_GREY', 'DARK_GREEN', 'LIGHT_BLUE', 'HIGHLIGHT_COLOR', 'SELECTED_COLOR',
    
    # Game classes
    'GameState', 'Player', 'Card', 'CapsaClientCard',
    
    # Game functions
    'deal', 'who_starts', 'value_checker', 'quantity_checker', 'play',
    
    # UI functions
    'show_session_menu', 'get_session_name', 'get_creator_name',
    'get_player_name', 'show_sessions_list', 'init_pygame', 'draw_game',
    
    # Server classes
    'CapsaGameServer', 'GameSession', 'CapsaGameState',
    
    # Card data
    'deck', 'card_sets', 'unordered_set'
]