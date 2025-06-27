import pygame
import sys
import json
import threading
import logging
import time
import math
import requests

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

try:
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
        
        if PYGAME_CARDS_AVAILABLE:
            big2_value = (self.value + 1) % 13
            self.pygame_card = card_sets[big2_value + 13 * self.suit]
        
        self.rect = pygame.Rect(0, 0, CARD_WIDTH, CARD_HEIGHT)

    def display(self, screen, left, top, selected=False):
        self.rect = pygame.Rect(left, top, CARD_WIDTH, CARD_HEIGHT)

        if PYGAME_CARDS_AVAILABLE:
            card_image = pygame.transform.scale(
                self.pygame_card.graphics.surface, (CARD_WIDTH, CARD_HEIGHT)
            )
            screen.blit(card_image, (left, top))
        else:
            pygame.draw.rect(screen, WHITE, self.rect)
            pygame.draw.rect(screen, BLACK, self.rect, 2)
            
            suits = ['♦', '♣', '♥', '♠']
            suit_colors = [RED, BLACK, RED, BLACK]
            
            font = pygame.font.Font(None, 24)
            text = font.render(f"{self.pp_value}", True, suit_colors[self.suit])
            screen.blit(text, (left + 5, top + 5))
            
            suit_font = pygame.font.Font(None, 36)
            suit_text = suit_font.render(suits[self.suit], True, suit_colors[self.suit])
            screen.blit(suit_text, (left + CARD_WIDTH//2 - 10, top + CARD_HEIGHT//2 - 15))

        if selected:
            pygame.draw.rect(screen, LIGHT_BLUE, self.rect, 5)

        return self.rect

class CapsaHTTPClient:
    def __init__(self):
        self.connected = False
        self.session_id = None
        self.session_name = ""
        self.player_index = -1
        self.player_name = ""
        self.client_id = None
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
        self.server_url = 'http://localhost:8080'
        self.selected_cards = []
        self.message = ""
        self.message_timer = 0
        self.in_session = False
        
    def connect_to_server(self):
        try:
            response = requests.post(f'{self.server_url}/api/game', 
                                   json={'client_name': 'Player'},
                                   timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.client_id = data.get('client_id')
                self.connected = True
                
                update_thread = threading.Thread(target=self.update_game_state, daemon=True)
                update_thread.start()
                
                print("Connected to server")
                return True
            else:
                print(f"Failed to connect: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def update_game_state(self):
        while self.connected:
            try:
                if self.in_session:
                    response = requests.post(f'{self.server_url}/api/game',
                                           json={
                                               'client_id': self.client_id,
                                               'command': 'GET_GAME_STATE'
                                           },
                                           timeout=5)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'command' in data and data['command'] == 'GAME_UPDATE':
                            self.game_data.update(data)
                
                time.sleep(0.001)
                
            except Exception as e:
                if self.connected:
                    logging.warning(f"Update error: {e}")
                time.sleep(0.05)
    
    def send_command(self, command):
        if not self.connected:
            return None
            
        try:
            command['client_id'] = self.client_id
            response = requests.post(f'{self.server_url}/api/game',
                                   json=command,
                                   timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Request failed: {response.status_code}")
                return None
                
        except Exception as e:
            logging.warning(f"Send error: {e}")
            return None
    
    def handle_session_menu(self):
        while True:
            choice = show_session_menu()
            
            if choice == 1:
                session_name = get_session_name()
                creator_name = get_creator_name()
                
                response = self.send_command({
                    'command': 'CREATE_SESSION',
                    'session_name': session_name,
                    'creator_name': creator_name
                })
                
                if response and 'command' in response and response['command'] == 'SESSION_JOINED':
                    self.session_id = response.get('session_id')
                    self.session_name = response.get('session_name')
                    self.player_index = response.get('player_index')
                    self.player_name = response.get('player_name')
                    self.in_session = True
                    
                    print(f"Berhasil membuat session '{self.session_name}' sebagai {self.player_name}")
                    print("Membuka game UI...")
                    return
                else:
                    print("Gagal membuat session")
                
            elif choice == 2:
                response = self.send_command({'command': 'LIST_SESSIONS'})
                
                if response and 'sessions' in response:
                    session_id = show_sessions_list(response['sessions'])
                    
                    if session_id:
                        player_name = get_player_name()
                        
                        response = self.send_command({
                            'command': 'JOIN_SESSION',
                            'session_id': session_id,
                            'player_name': player_name
                        })
                        
                        if response and 'command' in response and response['command'] == 'SESSION_JOINED':
                            self.session_id = response.get('session_id')
                            self.session_name = response.get('session_name')
                            self.player_index = response.get('player_index')
                            self.player_name = response.get('player_name')
                            self.in_session = True
                            
                            print(f"Berhasil join session '{self.session_name}' sebagai {self.player_name}")
                            print("Membuka game UI...")
                            return
                        elif response and 'error' in response:
                            print(f"Gagal join session: {response['error']}")
                        else:
                            print("Gagal join session")
                else:
                    print("Gagal mendapatkan daftar session")
                    
            elif choice == 3:
                print("Goodbye!")
                sys.exit(0)
    
    def show_message(self, message, duration=180):
        self.message = message
        self.message_timer = duration

def draw_game(screen, client, WIDTH, HEIGHT):
    screen.fill(DARK_GREEN)
    
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
    
    title = font_large.render(f"CAPSA MULTIPLAYER HTTP - {client.session_name}", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 10))
    
    if client.player_name:
        player_text = font_medium.render(f"You: {client.player_name}", True, LIGHT_BLUE)
        screen.blit(player_text, (10, 50))
    
    current_text = font_medium.render(f"Turn: {client.game_data['current_player_name']}", True, WHITE)
    screen.blit(current_text, (10, 80))
    
    y_pos = 120
    title_players = font_medium.render("Players:", True, WHITE)
    screen.blit(title_players, (10, y_pos))
    y_pos += 30
    
    for i, name in enumerate(client.game_data['players_names']):
        if name:
            count = client.game_data['players_card_counts'][i] if i < len(client.game_data['players_card_counts']) else 0
            
            if i == client.game_data['current_player_index']:
                color = LIGHT_BLUE
                prefix = "► "
            elif i == client.player_index:
                color = LIGHT_BLUE
                prefix = "● "
            else:
                color = WHITE
                prefix = "  "
            
            text = font_small.render(f"{prefix}Slot {i+1}: {name} ({count} cards)", True, color)
            screen.blit(text, (15, y_pos))
            y_pos += 25
    
    if client.game_data['played_cards']:
        center_x = WIDTH // 2
        center_y = HEIGHT // 2
        
        played_cards = [CapsaClientCard(card_data) for card_data in client.game_data['played_cards']]
        start_x = center_x - (len(played_cards) * (CARD_WIDTH + 5) // 2)
        
        for i, card in enumerate(played_cards):
            x = start_x + i * (CARD_WIDTH + 5)
            y = center_y - CARD_HEIGHT // 2
            card.display(screen, x, y)
    
    card_rects = []
    if client.game_data['my_hand']:
        my_cards = [CapsaClientCard(card_data) for card_data in client.game_data['my_hand']]
        
        start_x = 50
        start_y = HEIGHT - CARD_HEIGHT - 50
        card_spacing = min(50, (WIDTH - 100) // len(my_cards))
        
        for i, card in enumerate(my_cards):
            x = start_x + i * card_spacing
            selected = card.number in [c['number'] for c in client.selected_cards]
            y = start_y - (20 if selected else 0)
            
            rect = card.display(screen, x, y, selected)
            card_rects.append((rect, client.game_data['my_hand'][i]))
    
    button_rects = []
    if (client.game_data['game_active'] and 
        client.player_index == client.game_data['current_player_index']):
        
        play_rect = pygame.Rect(WIDTH - 200, HEIGHT - 100, 80, 40)
        pygame.draw.rect(screen, GREEN, play_rect)
        pygame.draw.rect(screen, BLACK, play_rect, 2)
        play_text = font_medium.render("PLAY", True, WHITE)
        screen.blit(play_text, (play_rect.x + 20, play_rect.y + 12))
        button_rects.append(('PLAY', play_rect))
        
        pass_rect = pygame.Rect(WIDTH - 110, HEIGHT - 100, 80, 40)
        pygame.draw.rect(screen, RED, pass_rect)
        pygame.draw.rect(screen, BLACK, pass_rect, 2)
        pass_text = font_medium.render("PASS", True, WHITE)
        screen.blit(pass_text, (pass_rect.x + 20, pass_rect.y + 12))
        button_rects.append(('PASS', pass_rect))
    
    if not client.game_data['game_active']:
        start_rect = pygame.Rect(WIDTH//2 - 60, HEIGHT - 60, 120, 40)
        pygame.draw.rect(screen, BLUE, start_rect)
        pygame.draw.rect(screen, BLACK, start_rect, 2)
        start_text = font_medium.render("START GAME", True, WHITE)
        screen.blit(start_text, (start_rect.x + 10, start_rect.y + 12))
        button_rects.append(('START', start_rect))
    
    if client.message and client.message_timer > 0:
        msg_text = font_medium.render(client.message, True, WHITE)
        msg_rect = msg_text.get_rect(center=(WIDTH//2, 100))
        pygame.draw.rect(screen, BLACK, msg_rect.inflate(20, 10))
        pygame.draw.rect(screen, WHITE, msg_rect.inflate(20, 10), 2)
        screen.blit(msg_text, msg_rect)
        client.message_timer -= 1
    
    return card_rects, button_rects

def main():
    client = CapsaHTTPClient()
    
    if not client.connect_to_server():
        print("Failed to connect to server")
        return
    
    client.handle_session_menu()
    
    screen, clock, WIDTH, HEIGHT, FPS = init_pygame()
    
    print("Starting game UI...")
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                card_rects, button_rects = draw_game(screen, client, WIDTH, HEIGHT)
                
                for rect, card in card_rects:
                    if rect.collidepoint(event.pos):
                        if card in client.selected_cards:
                            client.selected_cards.remove(card)
                        else:
                            client.selected_cards.append(card)
                        print(f"Card clicked: {card['pp_value']} of suit {card['suit']}")
                        break
                
                for button_type, rect in button_rects:
                    if rect.collidepoint(event.pos):
                        print(f"Button clicked: {button_type}")
                        if button_type == 'PLAY' and client.selected_cards:
                            card_numbers = [card['number'] for card in client.selected_cards]
                            print(f"Playing cards: {card_numbers}")
                            response = client.send_command({
                                'command': 'PLAY_CARDS',
                                'cards': card_numbers
                            })
                            if response and 'error' in response:
                                client.show_message(response['error'])
                            elif response and 'winner' in response:
                                client.show_message(f"{response['winner']} wins!")
                            client.selected_cards.clear()
                        elif button_type == 'PASS':
                            print("Passing turn")
                            response = client.send_command({'command': 'PASS_TURN'})
                            if response and 'error' in response:
                                client.show_message(response['error'])
                            client.selected_cards.clear()
                        elif button_type == 'START':
                            print("Starting game")
                            response = client.send_command({'command': 'START_GAME'})
                            if response and 'error' in response:
                                client.show_message(response['error'])
                        break
        
        draw_game(screen, client, WIDTH, HEIGHT)
        pygame.display.flip()
        clock.tick(FPS)
    
    client.connected = False
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()