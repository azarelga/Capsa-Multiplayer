import pygame
import sys
import socket
import json
import threading
import logging
import time
import math


# Import dari game.py untuk konsistensi
from game import (
    CARD_WIDTH, CARD_HEIGHT, WHITE, BLACK, RED, GREEN, BLUE, DARK_GREEN, 
    LIGHT_BLUE, GREY, LIGHT_GREY,
    card_sets
)
def show_session_menu():
    print("\n" + "="*50)
    print("CAPSA MULTIPLAYER - SESSION SELECTION")
    print("="*50)
    print("1. Buat session baru")
    print("2. Join session yang sudah ada")
    print("3. Keluar")
    print("="*50)
    
    while True:
        try:
            choice = input("Pilih opsi (1-3): ").strip()
            if choice in ['1', '2', '3']:
                return int(choice)
            else:
                print("Pilihan tidak valid. Ketik 1, 2, atau 3.")
        except KeyboardInterrupt:
            print("\n Goodbye!")
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
            print("- Nama tidak boleh kosong.")

def get_player_name():
    while True:
        player_name = input("Masukkan nama Anda: ").strip()
        if player_name:
            return player_name
        else:
            print("- Nama tidak boleh kosong.")

def show_sessions_list(sessions):
    if not sessions:
        print("\n- Tidak ada session yang tersedia.")
        return None
    
    print("\n- DAFTAR SESSION YANG TERSEDIA:")
    print("-" * 70)
    print(f"{'No':<3} {'Nama Session':<20} {'Creator':<15} {'Players':<8} {'Dibuat':<15}")
    print("-" * 70)
    
    for i, session in enumerate(sessions, 1):
        print(f"{i:<3} {session['session_name']:<20} {session['creator_name']:<15} "
              f"{session['player_count']}/4{'':<3} {session['created_at']:<15}")
    
    print("-" * 70)
    
    while True:
        try:
            choice = input(f"Pilih session (1-{len(sessions)}) atau 0 untuk kembali: ").strip()
            if choice == '0':
                return None
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(sessions):
                return sessions[choice_num - 1]['session_id']
            else:
                print(f"- Pilihan tidak valid. Ketik 1-{len(sessions)} atau 0.")
        except ValueError:
            print("- Masukkan angka yang valid.")
        except KeyboardInterrupt:
            print("\n- Goodbye!")
            sys.exit(0)

# Initialize Pygame (will be called after session selection)
def init_pygame():
    pygame.init()
    
    WIDTH, HEIGHT = 1200, 800
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Capsa Multiplayer")
    
    clock = pygame.time.Clock()
    FPS = 60
    
    return screen, clock, WIDTH, HEIGHT, FPS

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

        # Highlight if selected seperti di game.py
        if selected:
            pygame.draw.rect(screen, LIGHT_BLUE, self.rect, 5)

        return self.rect

class CapsaClient:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.session_id = None
        self.session_name = ""
        self.player_index = -1
        self.player_name = ""
        self.game_data = {
            'current_player_index': 0,
            'current_player_name': '',
            'players_names': ['', '', '', ''],
            'my_hand': [],
            'played_cards': [],
            'players_card_counts': [0, 0, 0, 0],
            'game_active': False,
            'winner': None,
            'players_passed': []
        }
        self.server_address = ('localhost', 55556) #IP LoadBalancer
        # self.server_address = ('57.155.178.71', 55556) #IP LoadBalancer
        self.selected_cards = []
        self.message = ""
        self.message_timer = 0
        self.in_session = False
        
    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(self.server_address)
            self.connected = True
            
            # Start listening thread
            listen_thread = threading.Thread(target=self.listen_server, daemon=True)
            listen_thread.start()
            
            print("- Connected to server")
            return True
            
        except Exception as e:
            print(f"- Failed to connect: {e}")
            return False
    
    def listen_server(self):
        buffer = ""
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if data:
                    buffer += data.decode()
                    
                    # Process complete messages
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line.strip():
                            try:
                                message = json.loads(line.strip())
                                self.handle_server_message(message)
                            except json.JSONDecodeError as e:
                                logging.warning(f"Invalid JSON: {line}")
                else:
                    break
                    
            except Exception as e:
                if self.connected:
                    logging.warning(f"Listen error: {e}")
                break
        
        self.connected = False
        print("- Disconnected from server")
    
    def handle_server_message(self, message):
        cmd = message.get('command')
        
        if cmd == 'SESSION_MENU':
            self.handle_session_menu(message.get('sessions', []))
            
        elif cmd == 'SESSION_JOINED':
            self.session_id = message.get('session_id')
            self.session_name = message.get('session_name')
            self.player_index = message.get('player_index')
            self.player_name = message.get('player_name')
            self.in_session = True
            
            print(f"- Berhasil join session '{self.session_name}' sebagai {self.player_name}")
            print("- Membuka game UI...")
            
        elif cmd == 'PLAYER_JOINED':
            # Show when other players join
            join_player_name = message.get('player_name')
            if join_player_name != self.player_name:  # Don't show our own join
                print(f"- {join_player_name} joined the session!")
                
        elif cmd == 'GAME_UPDATE':
            self.game_data.update(message)
            
        elif cmd == 'GAME_END':
            self.game_data['winner'] = message.get('winner')
            self.game_data['game_active'] = False
            self.show_message(f"{message.get('winner')} wins!")
            
        elif cmd == 'ERROR':
            error_msg = message.get('message', 'Error')
            print(f"- Error: {error_msg}")
            self.show_message(error_msg)
    
    def handle_session_menu(self, sessions):
        while True:
            choice = show_session_menu()
            
            if choice == 1:  # Create new session
                session_name = get_session_name()
                creator_name = get_creator_name()
                
                self.send_command({
                    'command': 'CREATE_SESSION',
                    'session_name': session_name,
                    'creator_name': creator_name
                })
                
                print(f"- Creating session '{session_name}'...")
                time.sleep(1)  # Wait for server response
                return  # Exit menu loop
                
            elif choice == 2:  # Join existing session
                session_id = show_sessions_list(sessions)
                
                if session_id:
                    # Ask for player name when joining
                    player_name = get_player_name()
                    
                    self.send_command({
                        'command': 'JOIN_SESSION',
                        'session_id': session_id,
                        'player_name': player_name  # Send player name
                    })
                    
                    print(f"- Joining session as '{player_name}'...")
                    time.sleep(1)  # Wait for server response
                    return  # Exit menu loop
                else:
                    # Request updated session list
                    self.send_command({'command': 'LIST_SESSIONS'})
                    time.sleep(0.5)  # Wait for server response
                    
            elif choice == 3:  # Exit
                print("- Goodbye!")
                sys.exit(0)
    
    def send_command(self, command):
        """Send command to server"""
        if self.connected:
            try:
                message = json.dumps(command) + '\n'
                self.socket.send(message.encode())
                return True
            except Exception as e:
                logging.warning(f"Send error: {e}")
                self.connected = False
                return False
        return False
    
    def show_message(self, message, duration=180):
        self.message = message
        self.message_timer = duration

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
        player_text = font_medium.render(f"You: {client.player_name}", True, LIGHT_BLUE)
        screen.blit(player_text, (10, 50))
    
    # Current player with custom names
    current_text = font_medium.render(f"Turn: {client.game_data['current_player_name']}", True, WHITE)
    screen.blit(current_text, (10, 80))
    
    # Players info with custom names and better formatting
    y_pos = 120
    title_players = font_medium.render("Players:", True, WHITE)
    screen.blit(title_players, (10, y_pos))
    y_pos += 30
    
    for i, name in enumerate(client.game_data['players_names']):
        if name:
            count = client.game_data['players_card_counts'][i] if i < len(client.game_data['players_card_counts']) else 0
            
            # Highlight current player and yourself differently
            if i == client.game_data['current_player_index']:
                color = LIGHT_BLUE
                prefix = "► "
            elif i == client.player_index:
                color = LIGHT_BLUE
                prefix = "● "
            else:
                color = WHITE
                prefix = "  "
            
            # Show slot number and custom name
            text = font_small.render(f"{prefix}Slot {i+1}: {name} ({count} cards)", True, color)
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
        my_cards = [CapsaClientCard(card_data) for card_data in client.game_data['my_hand']]
        
        start_x = 50
        start_y = HEIGHT - CARD_HEIGHT - 50
        card_spacing = min(50, (WIDTH - 100) // len(my_cards))
        
        for i, card in enumerate(my_cards):
            x = start_x + i * card_spacing
            selected = card.number in [c['number'] for c in client.selected_cards]
            y = start_y - (20 if selected else 0)  # Raise selected cards
            
            rect = card.display(screen, x, y, selected)
            card_rects.append((rect, client.game_data['my_hand'][i]))  # Return original data
    
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
    
    return card_rects, button_rects

def main():
    # Terminal session selection first
    client = CapsaClient()
    
    if not client.connect_to_server():
        print("- Failed to connect to server")
        return
    
    # Wait for session selection to complete
    print("- Waiting for session selection...")
    while not client.in_session:
        time.sleep(0.1)
    
    # Initialize pygame after session is joined
    screen, clock, WIDTH, HEIGHT, FPS = init_pygame()
    
    print("- Starting game UI...")
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                card_rects, button_rects = draw_game(screen, client, WIDTH, HEIGHT)
                
                # Handle card clicks
                for rect, card in card_rects:
                    if rect.collidepoint(event.pos):
                        if card in client.selected_cards:
                            client.selected_cards.remove(card)
                        else:
                            client.selected_cards.append(card)
                        print(f"Card clicked: {card['pp_value']} of suit {card['suit']}")
                        break
                
                # Handle button clicks
                for button_type, rect in button_rects:
                    if rect.collidepoint(event.pos):
                        print(f"Button clicked: {button_type}")
                        if button_type == 'PLAY' and client.selected_cards:
                            card_numbers = [card['number'] for card in client.selected_cards]
                            print(f"Playing cards: {card_numbers}")
                            client.send_command({
                                'command': 'PLAY_CARDS',
                                'cards': card_numbers
                            })
                            client.selected_cards.clear()
                        elif button_type == 'PASS':
                            print("Passing turn")
                            client.send_command({'command': 'PASS_TURN'})
                            client.selected_cards.clear()
                        elif button_type == 'START':
                            print("Starting game")
                            client.send_command({'command': 'START_GAME'})
                        break
        
        # Draw everything
        draw_game(screen, client, WIDTH, HEIGHT)
        pygame.display.flip()
        clock.tick(FPS)
    
    # Cleanup
    if client.connected:
        try:
            client.socket.close()
        except:
            pass
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()