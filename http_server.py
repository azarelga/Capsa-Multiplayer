import json
import threading
import time
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

from game import (
    Card, Player, deal, who_starts, play, value_checker, quantity_checker, deck,
    CARD_WIDTH, CARD_HEIGHT, WHITE, BLACK, RED, GREEN, BLUE, PURPLE, GREY, 
    LIGHT_GREY, DARK_GREEN, LIGHT_BLUE, WINDOW_WIDTH, WINDOW_HEIGHT
)

class GameSession:
    def __init__(self, session_id, session_name, creator_name):
        self.session_id = session_id
        self.session_name = session_name
        self.creator_name = creator_name
        self.created_at = datetime.now()
        self.clients = {}
        self.game_state = CapsaGameState()
        self.status = "waiting"

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'session_name': self.session_name,
            'creator_name': self.creator_name,
            'created_at': self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'player_count': len(self.clients),
            'status': self.status
        }

class CapsaGameState:
    def __init__(self):
        self.reset_game()

    def reset_game(self):
        self.current_player_index = 0
        self.played_cards = []
        self.played_cards_history = []
        self.players_passed = set()
        self.round_passes = set()
        self.game_active = False
        self.winner = None
        self.players = []
        self.players_names = ["", "", "", ""]
        self.turn_order = []

        for i in range(4):
            self.players.append(Player(f"Player {i+1}"))

class CapsaGameServer:
    def __init__(self):
        self.sessions = {}
        self.clients = {}
        self.lock = threading.Lock()
        self.running = True
        self.ai_names = ["AI Bot 1", "AI Bot 2", "AI Bot 3", "AI Bot 4"]

    def add_client(self, client_id, client_name):
        with self.lock:
            print(f"Adding client {client_id}")
            
            self.clients[client_id] = {
                'session_id': None,
                'name': client_name,
                'player_index': -1,
                'last_seen': time.time()
            }

    def update_client_activity(self, client_id):
        if client_id in self.clients:
            self.clients[client_id]['last_seen'] = time.time()

    def cleanup_inactive_clients(self):
        current_time = time.time()
        inactive_clients = []
        
        for client_id, client_info in self.clients.items():
            if current_time - client_info['last_seen'] > 60:  # 60 seconds timeout
                inactive_clients.append(client_id)
        
        for client_id in inactive_clients:
            self.remove_client(client_id)

    def handle_command(self, client_id, command):
        self.update_client_activity(client_id)
        cmd_type = command.get('command')

        if cmd_type == 'CREATE_SESSION':
            session_name = command.get('session_name', 'Unnamed Session')
            creator_name = command.get('creator_name', 'Anonymous')
            return self.create_session(client_id, session_name, creator_name)
            
        elif cmd_type == 'JOIN_SESSION':
            session_id = command.get('session_id')
            player_name = command.get('player_name', 'Anonymous')
            return self.join_session(client_id, session_id, player_name)
            
        elif cmd_type == 'LIST_SESSIONS':
            return self.get_sessions_list()
            
        elif cmd_type == 'PLAY_CARDS':
            card_numbers = command.get('cards', [])
            return self.handle_play_cards(client_id, card_numbers)
            
        elif cmd_type == 'PASS_TURN':
            return self.handle_pass_turn(client_id)
            
        elif cmd_type == 'START_GAME':
            return self.start_new_game(client_id)

        elif cmd_type == 'GET_GAME_STATE':
            return self.get_game_state(client_id)
            
        else:
            return {'error': f'Unknown command: {cmd_type}'}

    def get_sessions_list(self):
        sessions_list = []
        for session in self.sessions.values():
            sessions_list.append(session.to_dict())
        return {'command': 'SESSION_MENU', 'sessions': sessions_list}

    def create_session(self, client_id, session_name, creator_name):
        with self.lock:
            session_id = str(uuid.uuid4())[:8]
            
            session = GameSession(session_id, session_name, creator_name)
            self.sessions[session_id] = session
            
            client_info = self.clients[client_id]
            client_info['session_id'] = session_id
            client_info['name'] = creator_name
            client_info['player_index'] = 0

            session.clients[client_id] = client_info
            
            session.game_state.players[0].name = creator_name
            session.game_state.players_names[0] = creator_name

            print(f"Session '{session_name}' created by {creator_name} (ID: {session_id})")

            return {
                'command': 'SESSION_JOINED',
                'session_id': session_id,
                'session_name': session_name,
                'player_index': 0,
                'player_name': creator_name
            }

    def join_session(self, client_id, session_id, player_name):
        with self.lock:
            if session_id not in self.sessions:
                return {'error': 'Session not found'}

            session = self.sessions[session_id]
            
            if len(session.clients) >= 4:
                return {'error': 'Session is full (4 players max)'}

            taken_slots = [c.get('player_index') for c in session.clients.values()]
            available_slots = [i for i in range(4) if i not in taken_slots]
            
            if not available_slots:
                return {'error': 'No available slots'}

            player_index = available_slots[0]
            
            if not player_name or len(player_name.strip()) == 0:
                player_name = f"Player {player_index + 1}"
            else:
                player_name = player_name.strip()[:20]
                
            existing_names = [c.get('name', '').lower() for c in session.clients.values()]
            original_name = player_name
            counter = 1
            while player_name.lower() in existing_names:
                player_name = f"{original_name}_{counter}"
                counter += 1

            client_info = self.clients[client_id]
            client_info['session_id'] = session_id
            client_info['player_index'] = player_index
            client_info['name'] = player_name

            session.clients[client_id] = client_info
            
            session.game_state.players[player_index].name = player_name
            session.game_state.players_names[player_index] = player_name

            print(f"{player_name} joined session '{session.session_name}' (ID: {session_id}) as Player {player_index + 1}")

            return {
                'command': 'SESSION_JOINED',
                'session_id': session_id,
                'session_name': session.session_name,
                'player_index': player_index,
                'player_name': player_name
            }

    def remove_client(self, client_id):
        with self.lock:
            if client_id not in self.clients:
                return

            client_info = self.clients[client_id]
            session_id = client_info.get('session_id')

            if session_id and session_id in self.sessions:
                session = self.sessions[session_id]
                player_index = client_info.get('player_index', -1)
                player_name = client_info.get('name', 'Unknown')

                if client_id in session.clients:
                    del session.clients[client_id]

                if player_index >= 0:
                    ai_name = self.ai_names[player_index]
                    session.game_state.players[player_index].name = ai_name
                    session.game_state.players_names[player_index] = ai_name

                print(f"{player_name} left session '{session.session_name}', replaced with {ai_name}")

                if len(session.clients) == 0:
                    del self.sessions[session_id]
                    print(f"Empty session '{session.session_name}' removed")

            del self.clients[client_id]

    def get_session(self, client_id):
        client_info = self.clients.get(client_id)
        if not client_info:
            return None
        
        session_id = client_info.get('session_id')
        return self.sessions.get(session_id)

    def get_game_state(self, client_id):
        session = self.get_session(client_id)
        if not session:
            return {'error': 'No session found'}

        client_info = self.clients.get(client_id)
        if not client_info:
            return {'error': 'Client not found'}

        player_index = client_info['player_index']
        my_hand = [self.card_to_dict(card) for card in session.game_state.players[player_index].hand]
        played_cards_data = [self.card_to_dict(card) for card in session.game_state.played_cards]

        return {
            'command': 'GAME_UPDATE',
            'session_id': session.session_id,
            'session_name': session.session_name,
            'current_player_index': session.game_state.current_player_index,
            'current_player_name': session.game_state.players[session.game_state.current_player_index].name,
            'players_names': [p.name for p in session.game_state.players],
            'my_hand': my_hand,
            'my_player_index': client_info['player_index'],
            'played_cards': played_cards_data,
            'players_card_counts': [len(p.hand) for p in session.game_state.players],
            'game_active': session.game_state.game_active,
            'winner': session.game_state.winner,
            'players_passed': list(session.game_state.round_passes)
        }

    def handle_play_cards(self, client_id, card_numbers):
        session = self.get_session(client_id)
        if not session:
            return {'error': 'No session found'}

        with self.lock:
            if not session.game_state.game_active:
                return {'error': 'Game not active'}

            client_info = self.clients.get(client_id)
            player_index = client_info['player_index']

            if player_index != session.game_state.current_player_index:
                return {'error': 'Not your turn!'}

            current_player = session.game_state.players[player_index]
            
            selected_cards = []
            for card_num in card_numbers:
                for card in current_player.hand:
                    if card.number == card_num:
                        selected_cards.append(card)
                        break

            if len(selected_cards) != len(card_numbers):
                return {'error': 'Invalid cards selected'}

            selected_cards.sort(key=lambda card: card.number)
            
            result = play(selected_cards, current_player.hand, session.game_state.played_cards)

            if result == 0:
                for card in selected_cards:
                    current_player.hand.remove(card)
                    card.selected = False
                    card.selected_by = current_player.name

                session.game_state.played_cards = selected_cards
                session.game_state.played_cards_history.append(selected_cards.copy())
                
                session.game_state.round_passes.clear()

                if len(current_player.hand) == 0:
                    self.end_game(session, current_player.name)
                    return {'success': 'Cards played', 'winner': current_player.name}

                self.next_turn(session)
                return {'success': 'Cards played'}

            else:
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
                    10: "You need to play a better hand!"
                }

                return {'error': error_messages.get(result, 'Invalid play')}

    def handle_pass_turn(self, client_id):
        session = self.get_session(client_id)
        if not session:
            return {'error': 'No session found'}

        with self.lock:
            if not session.game_state.game_active:
                return {'error': 'Game not active'}

            client_info = self.clients.get(client_id)
            player_index = client_info['player_index']

            if player_index != session.game_state.current_player_index:
                return {'error': 'Not your turn!'}

            session.game_state.round_passes.add(player_index)

            if len(session.game_state.round_passes) >= 3:
                session.game_state.played_cards = []
                session.game_state.played_cards_history.clear()
                session.game_state.round_passes.clear()

            self.next_turn(session)
            return {'success': 'Turn passed'}

    def next_turn(self, session):
        session.game_state.current_player_index = (session.game_state.current_player_index + 1) % 4

        attempts = 0
        while (session.game_state.current_player_index in session.game_state.round_passes and
               attempts < 4):
            session.game_state.current_player_index = (session.game_state.current_player_index + 1) % 4
            attempts += 1

        current_player_id = None
        for client_id, info in session.clients.items():
            if info['player_index'] == session.game_state.current_player_index:
                current_player_id = client_id
                break

        if current_player_id is None:
            threading.Timer(2.0, lambda: self.handle_ai_turn(session)).start()

    def handle_ai_turn(self, session):
        with self.lock:
            if not session.game_state.game_active:
                return

            player_index = session.game_state.current_player_index
            current_player = session.game_state.players[player_index]

            if not current_player.hand:
                return

            played = False
            for card in current_player.hand:
                if play([card], current_player.hand, session.game_state.played_cards) == 0:
                    current_player.hand.remove(card)
                    session.game_state.played_cards = [card]
                    for c in session.game_state.played_cards:
                        c.selected_by = current_player.name
                    session.game_state.played_cards_history.append([card])
                    
                    session.game_state.round_passes.clear()
                    played = True
                    break

            if not played:
                session.game_state.round_passes.add(player_index)

                if len(session.game_state.round_passes) >= 3:
                    session.game_state.played_cards = []
                    session.game_state.played_cards_history.clear()
                    session.game_state.round_passes.clear()

            if len(current_player.hand) == 0:
                self.end_game(session, current_player.name)
                return

            self.next_turn(session)

    def start_new_game(self, client_id):
        session = self.get_session(client_id)
        if not session:
            return {'error': 'No session found'}

        with self.lock:
            if len(session.clients) == 0:
                return {'error': 'No players in session'}

            session.game_state.reset_game()
            session.status = "playing"

            for i in range(4):
                human_in_slot = False
                for client_id, client_info in session.clients.items():
                    if client_info['player_index'] == i:
                        session.game_state.players[i].name = client_info['name']
                        session.game_state.players_names[i] = client_info['name']
                        human_in_slot = True
                        break
                
                if not human_in_slot:
                    session.game_state.players[i].name = self.ai_names[i]
                    session.game_state.players_names[i] = self.ai_names[i]

            deal(session.game_state.players)

            starting_player = who_starts(session.game_state.players)
            session.game_state.current_player_index = session.game_state.players.index(starting_player)

            session.game_state.game_active = True

            print(f"New Capsa game started in session '{session.session_name}'!")
            print(f"Players: {[p.name for p in session.game_state.players]}")
            print(f"Starting player: {starting_player.name}")

            starting_is_human = any(
                info['player_index'] == session.game_state.current_player_index
                for info in session.clients.values()
            )

            if not starting_is_human:
                threading.Timer(2.0, lambda: self.handle_ai_turn(session)).start()

            return {'success': 'Game started'}

    def end_game(self, session, winner_name):
        session.game_state.game_active = False
        session.game_state.winner = winner_name
        session.status = "finished"

        print(f"Game ended in session '{session.session_name}'! Winner: {winner_name}")

        threading.Timer(5.0, lambda: self.auto_restart_game(session)).start()

    def auto_restart_game(self, session):
        if len(session.clients) > 0:
            session.status = "waiting"

    def card_to_dict(self, card):
        return {
            'number': card.number,
            'suit': card.suit,
            'value': card.value,
            'pp_value': card.pp_value,
            'selected': getattr(card, 'selected', False)
        }

game_server = CapsaGameServer()

class CapsaHTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)
            
            if path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'<h1>Capsa Multiplayer HTTP Server</h1><p>Server is running!</p>')
                
            elif path == '/api/ping':
                client_id = query_params.get('client_id', [''])[0]
                if client_id:
                    game_server.update_client_activity(client_id)
                
                self.send_json_response({'status': 'pong'})
                
            else:
                self.send_response(404)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(b'Not Found')
                
        except Exception as e:
            logging.error(f"GET error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'error': 'Invalid JSON'}, 400)
                return
            
            client_id = data.get('client_id')
            if not client_id:
                client_id = str(uuid.uuid4())
                client_name = data.get('client_name', f'Player_{client_id[:8]}')
                game_server.add_client(client_id, client_name)
                self.send_json_response({'client_id': client_id})
                return
            
            if client_id not in game_server.clients:
                client_name = data.get('client_name', f'Player_{client_id[:8]}')
                game_server.add_client(client_id, client_name)
            
            response = game_server.handle_command(client_id, data)
            self.send_json_response(response)
            
        except Exception as e:
            logging.error(f"POST error: {e}")
            self.send_json_response({'error': str(e)}, 500)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def send_json_response(self, data, status=200):
        response = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        pass

def cleanup_thread():
    while game_server.running:
        game_server.cleanup_inactive_clients()
        time.sleep(10)

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    server_address = ('', 8080)
    httpd = HTTPServer(server_address, CapsaHTTPHandler)
    
    cleanup_timer = threading.Thread(target=cleanup_thread, daemon=True)
    cleanup_timer.start()

    print("=" * 50)
    print("CAPSA MULTIPLAYER HTTP SERVER STARTED")
    print("=" * 50)
    print(f"Listening on port 8080")
    print(f"Connect clients to: http://localhost:8080")
    print(f"Supports 1-4 players (AI fills empty slots)")
    print("=" * 50)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        game_server.running = False
        httpd.shutdown()

if __name__ == "__main__":
    main()