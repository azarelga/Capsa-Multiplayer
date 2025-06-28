import pygame
import sys
import socket
import json
import threading
import logging
import time
import math

from game import (
    get_session_name, 
    get_creator_name, 
    get_player_name,
    draw_game,
    show_session_menu,
    show_sessions_list,
    init_pygame
)
from card import CapsaClientCard

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
        # self.server_address = ('localhost', 55556) #IP LoadBalancer
        self.server_address = ('57.155.178.71', 55556) #IP LoadBalancer
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
                            print(f"Card deselected: {card['pp_value']} of suit {card['suit']}")
                        else:
                            client.selected_cards.append(card)
                            print(f"Card selected: {card['pp_value']} of suit {card['suit']}")
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