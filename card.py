import pygame
from game import (
    CARD_WIDTH,
    CARD_HEIGHT,
    WHITE,
    BLACK,
    RED,
    card_sets,
    HIGHLIGHT_COLOR,
    SELECTED_COLOR
)

# Check pygame_cards availability
try:
    # Test if card_sets is available from game.py import
    test_card = card_sets[0] if card_sets else None
    PYGAME_CARDS_AVAILABLE = True
except (ImportError, NameError, IndexError):
    print("pygame_cards not available, using simple card display")
    PYGAME_CARDS_AVAILABLE = False


class CapsaClientCard:
    def __init__(self, card_data):
        self.number = card_data['number']
        self.suit = card_data['suit']
        self.value = card_data['value']
        self.pp_value = card_data['pp_value']
        self.selected = card_data.get('selected', False)
        
        # Setup pygame_cards graphics seperti di game.py
        if PYGAME_CARDS_AVAILABLE:
            big2_value = (self.value + 1) % 13
            self.pygame_card = card_sets[big2_value + 13 * self.suit]
        
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)

    def display(self, screen, left, top, selected=False):
        self.rect = pygame.Rect(left, top, CARD_WIDTH, CARD_HEIGHT)

        if PYGAME_CARDS_AVAILABLE:
            # Draw card using pygame_cards seperti di game.py
            card_image = pygame.transform.scale(
                self.pygame_card.graphics.surface, (CARD_WIDTH, CARD_HEIGHT)
            )
            screen.blit(card_image, (left, top))
        else:
            # Fallback simple drawing
            pygame.draw.rect(screen, WHITE, self.rect)
            pygame.draw.rect(screen, BLACK, self.rect, 2)
            
            # Draw suit and value
            suits = ['♦', '♣', '♥', '♠']
            suit_colors = [RED, BLACK, RED, BLACK]
            
            font = pygame.font.Font(None, 24)
            text = font.render(f"{self.pp_value}", True, suit_colors[self.suit])
            screen.blit(text, (left + 5, top + 5))
            
            suit_font = pygame.font.Font(None, 36)
            suit_text = suit_font.render(suits[self.suit], True, suit_colors[self.suit])
            screen.blit(suit_text, (left + CARD_WIDTH//2 - 10, top + CARD_HEIGHT//2 - 15))

        # Better highlight for selected cards
        if selected:
            # Draw a thick colored border around the selected card
            pygame.draw.rect(screen, SELECTED_COLOR, self.rect, 6)
            # Also draw a glow effect
            glow_rect = pygame.Rect(left - 3, top - 3, CARD_WIDTH + 6, CARD_HEIGHT + 6)
            pygame.draw.rect(screen, HIGHLIGHT_COLOR, glow_rect, 3)

        return self.rect