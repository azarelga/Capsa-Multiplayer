import sys
import os.path
import uuid
from glob import glob
from datetime import datetime
import threading
import time
import json
import logging
import random
import math
import redis
from enum import Enum

from game import (
    Card, Player, deal, who_starts, play, value_checker, quantity_checker, deck,
    CARD_WIDTH, CARD_HEIGHT, WHITE, BLACK, RED, GREEN, BLUE, PURPLE, GREY, 
    LIGHT_GREY, DARK_GREEN, LIGHT_BLUE, WINDOW_WIDTH, WINDOW_HEIGHT
)

REDIS_HOST = 'capsagamecache.redis.cache.windows.net'
REDIS_PORT = 6380 # 6380 for SSL/TLS, 6379 for non-SSL
REDIS_PASSWORD = ''
REDIS_DB = 0 # Default Redis database

try:
    redis_client = redis.StrictRedis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        # username='default',
        password=REDIS_PASSWORD,
        db=REDIS_DB,
        ssl=True, 
        decode_responses=True 
    )
    redis_client.ping()
    print("Successfully connected to Azure Cache for Redis.")
except redis.exceptions.ConnectionError as e:
    print(f"ERROR: Could not connect to Redis: {e}")
    sys.exit(1) # Exit if Redis connection fails at startup



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
        self.round_passes = set()  # Track passes for current round only
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

    def add_client(self, client_id, socket):
        with self.lock:
            print(f"Adding client {client_id}")
            
            self.clients[client_id] = {
                'socket': socket,
                'session_id': None,
                'name': f"User_{client_id.split(':')[-1]}",
                'player_index': -1
            }

            self.send_session_menu(client_id)

    def send_session_menu(self, client_id):
        sessions_list = []
        active_session_ids = redis_client.smembers("active_sessions")

        for sid in active_session_ids:
            session_data = redis_client.hgetall(f"session:{sid}")
            if session_data:
                session_data['player_count'] = int(session_data.get('player_count', '0'))
                sessions_list.append(session_data)
            else:
                redis_client.srem("active_sessions", sid) 

        self.send_to_client(client_id, {
            'command': 'SESSION_MENU',
            'sessions': sessions_list
        })

    def handle_command(self, client_id, command):
        cmd_type = command.get('command')

        if cmd_type == 'CREATE_SESSION':
            session_name = command.get('session_name', 'Unnamed Session')
            creator_name = command.get('creator_name', 'Anonymous')
            self.create_session(client_id, session_name, creator_name)
            
        elif cmd_type == 'JOIN_SESSION':
            session_id = command.get('session_id')
            player_name = command.get('player_name', 'Anonymous')
            self.join_session(client_id, session_id, player_name)
            
        elif cmd_type == 'LIST_SESSIONS':
            self.send_session_menu(client_id)
            
        elif cmd_type == 'PLAY_CARDS':
            card_numbers = command.get('cards', [])
            self.handle_play_cards(client_id, card_numbers)
            
        elif cmd_type == 'PASS_TURN':
            self.handle_pass_turn(client_id)
            
        elif cmd_type == 'START_GAME':
            self.start_new_game(client_id)
            
        else:
            logging.warning(f"Unknown command from {client_id}: {cmd_type}")

    # In CapsaGameServer class
    def create_session(self, client_id, session_name, creator_name):
        with self.lock:
            session_id = str(uuid.uuid4())[:8]
            
            session = GameSession(session_id, session_name, creator_name)
            self.sessions[session_id] = session # Store locally as this VM is managing it initially
            
            client_info = self.clients[client_id]
            client_info['session_id'] = session_id
            client_info['name'] = creator_name
            client_info['player_index'] = 0

            session.clients[client_id] = client_info
            
            session.game_state.players[0].name = creator_name
            session.game_state.players_names[0] = creator_name

            session_data = {
                "session_name": session_name,
                "creator_name": creator_name,
                "created_at": session.created_at.isoformat(),
                "player_count": 1,
                "status": "waiting",
                "game_state_json": json.dumps(self._get_initial_game_state_json())
            }
            redis_client.hmset(f"session:{session_id}", session_data)
            redis_client.sadd("active_sessions", session_id)

            print(f"Session '{session_name}' created by {creator_name} (ID: {session_id}) and stored in Redis.")

            self.send_to_client(client_id, {
                'command': 'SESSION_JOINED',
                'session_id': session_id,
                'session_name': session_name,
                'player_index': 0,
                'player_name': creator_name
            })

            self.broadcast_game_state_to_session(session_id)

    # Helper method to get initial game state as JSON (add this inside CapsaGameServer)
    def _get_initial_game_state_json(self):
        initial_state = CapsaGameState() # Create a temporary default state
        return {
            'current_player_index': initial_state.current_player_index,
            'played_cards': [], # Should be empty
            'players_names': initial_state.players_names,
            'players_card_counts': [0,0,0,0], # Initial card counts
            'game_active': initial_state.game_active,
            'winner': initial_state.winner,
            'players_passed': []
        }

    # In CapsaGameServer class
    def join_session(self, client_id, session_id, player_name):
        with self.lock:
            if session_id not in redis_client.sismember("active_sessions", session_id):
                self.send_to_client(client_id, {
                    'command': 'ERROR',
                    'message': 'Session not found or no longer active'
                })
                return

            pipe = redis_client.pipeline()
            pipe.watch(f"session:{session_id}")

            session_data_from_redis = pipe.hgetall(f"session:{session_id}")
            if not session_data_from_redis:
                pipe.unwatch()
                self.send_to_client(client_id, {'command': 'ERROR', 'message': 'Session not found (race condition)'})
                return

            current_player_count = int(session_data_from_redis.get('player_count', '0'))
            if current_player_count >= 4:
                pipe.unwatch()
                self.send_to_client(client_id, {'command': 'ERROR', 'message': 'Session is full (4 players max)'})
                return

            session_obj = self.sessions.get(session_id)
            if not session_obj:
                session_obj = GameSession(
                    session_id,
                    session_data_from_redis.get('session_name'),
                    session_data_from_redis.get('creator_name')
                )
                self.sessions[session_id] = session_obj

            taken_slots = [c.get('player_index') for c in session_obj.clients.values()]
            global_players_names = json.loads(session_data_from_redis.get('players_names_json', '["", "", "", ""]'))
            
            player_index = -1
            for i in range(4):
                if global_players_names[i] == "":
                    player_index = i
                    break
            
            if player_index == -1:
                pipe.unwatch()
                self.send_to_client(client_id, {'command': 'ERROR', 'message': 'No available player slots in session.'})
                return

            final_player_name = player_name.strip()[:20]
            if not final_player_name:
                final_player_name = f"Player {player_index + 1}"

            pipe.multi()
            pipe.hincrby(f"session:{session_id}", "player_count", 1)
            global_players_names[player_index] = final_player_name
            pipe.hset(f"session:{session_id}", "players_names_json", json.dumps(global_players_names))

            try:
                pipe.execute()
            except redis.exceptions.WatchError:
                self.send_to_client(client_id, {'command': 'ERROR', 'message': 'Failed to join: Session state changed. Try again.'})
                return

            # Update local state for the client that just joined this VM
            client_info = self.clients[client_id]
            client_info['session_id'] = session_id
            client_info['player_index'] = player_index
            client_info['name'] = final_player_name

            session_obj.clients[client_id] = client_info
            session_obj.game_state.players[player_index].name = final_player_name
            session_obj.game_state.players_names[player_index] = final_player_name

            print(f"{final_player_name} joined session '{session_obj.session_name}' (ID: {session_id}) as Player {player_index + 1}.")

            self.send_to_client(client_id, {
                'command': 'SESSION_JOINED',
                'session_id': session_id,
                'session_name': session_obj.session_name,
                'player_index': player_index,
                'player_name': final_player_name
            })

            self.broadcast_message_to_session(session_id, {
                'command': 'PLAYER_JOINED',
                'player_name': final_player_name,
                'player_index': player_index,
                'message': f"{final_player_name} joined the session!"
            })

            # Fetch updated game state from Redis and then broadcast it
            self.broadcast_game_state_to_session(session_id)

    # In CapsaGameServer class
    def remove_client(self, client_id):
        with self.lock:
            if client_id not in self.clients:
                return

            client_info = self.clients[client_id]
            session_id = client_info.get('session_id')
            player_index = client_info.get('player_index', -1)
            player_name = client_info.get('name', 'Unknown')

            if session_id and session_id in self.sessions:
                session = self.sessions[session_id]

                if client_id in session.clients:
                    del session.clients[client_id]

                if player_index >= 0:
                    pipe = redis_client.pipeline()
                    pipe.watch(f"session:{session_id}")
                    
                    session_data_from_redis = pipe.hgetall(f"session:{session_id}")
                    if session_data_from_redis:
                        global_players_names = json.loads(session_data_from_redis.get('players_names_json', '["", "", "", ""]'))
                        global_players_names[player_index] = ""

                        pipe.multi()
                        pipe.hincrby(f"session:{session_id}", "player_count", -1)
                        pipe.hset(f"session:{session_id}", "players_names_json", json.dumps(global_players_names))
                        try:
                            pipe.execute()
                        except redis.exceptions.WatchError:
                            logging.warning(f"Redis transaction failed for client removal: {client_id}")

                        updated_count = int(redis_client.hget(f"session:{session_id}", "player_count") or 0)
                        if updated_count <= 0:
                            redis_client.srem("active_sessions", session_id)
                            redis_client.delete(f"session:{session_id}")
                            print(f"Session '{session.session_name}' (ID: {session_id}) empty and removed from Redis.")
                    
                    session.game_state.players[player_index].name = self.ai_names[player_index]
                    session.game_state.players_names[player_index] = self.ai_names[player_index]


                print(f"{player_name} left session '{session.session_name}', replaced with {self.ai_names[player_index]}.")

                if len(session.clients) == 0 and not session_id in redis_client.smembers("active_sessions"):
                    del self.sessions[session_id] # Clean up local session if no clients left on this VM AND not globally active
                    print(f"Local session '{session.session_name}' removed.")
                else:
                    self.broadcast_game_state_to_session(session_id)

            del self.clients[client_id]

    def get_session(self, client_id):
        client_info = self.clients.get(client_id)
        if not client_info:
            return None
        
        session_id = client_info.get('session_id')
        return self.sessions.get(session_id)

    def handle_play_cards(self, client_id, card_numbers):
        session = self.get_session(client_id)
        if not session:
            return

        with self.lock:
            if not session.game_state.game_active:
                return

            client_info = self.clients.get(client_id)
            if not client_info:
                return

            player_index = client_info["player_index"]

            # Check if player has already passed in this round (check this FIRST)
            if player_index in session.game_state.round_passes:
                print(f"Player {player_index} tried to play after passing, sending error")
                self.send_to_client(
                    client_id, 
                    {
                        "command": "ERROR", 
                        "message": "You cannot play cards after passing. Wait for the next round."
                    }
                )
                return

            if player_index != session.game_state.current_player_index:
                self.send_to_client(
                    client_id, {"command": "ERROR", "message": "Not your turn!"}
                )
                return

            current_player = session.game_state.players[player_index]

            selected_cards = []
            for card_num in card_numbers:
                for card in current_player.hand:
                    if card.number == card_num:
                        selected_cards.append(card)
                        break

            if len(selected_cards) != len(card_numbers):
                self.send_to_client(
                    client_id, {"command": "ERROR", "message": "Invalid cards selected"}
                )
                return

            selected_cards.sort(key=lambda card: card.number)

            result = play(
                selected_cards, current_player.hand, session.game_state.played_cards
            )

            if result == 0:
                for card in selected_cards:
                    current_player.hand.remove(card)
                    card.selected = False
                    card.selected_by = current_player.name

                session.game_state.played_cards = selected_cards
                session.game_state.played_cards_history.append(selected_cards.copy())

                # DON'T clear round passes here - only clear when 3 players have passed
                print(f"Player {player_index} played cards - round continues")

                if len(current_player.hand) == 0:
                    self.end_game(session, current_player.name)
                    return

                self.next_turn(session)

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
                    10: "You need to play a better hand!",
                }

                self.send_to_client(
                    client_id,
                    {
                        "command": "ERROR",
                        "message": error_messages.get(result, "Invalid play"),
                    },
                )

    def handle_pass_turn(self, client_id):
        session = self.get_session(client_id)
        if not session:
            return

        with self.lock:
            if not session.game_state.game_active:
                return

            client_info = self.clients.get(client_id)
            player_index = client_info['player_index']

            if player_index != session.game_state.current_player_index:
                return

            # Add to round passes (this round only)
            session.game_state.round_passes.add(player_index)

            # Check if 3 players passed in this round (only 1 left)
            if len(session.game_state.round_passes) >= 3:
                # Clear the table and start new round with last player who played
                session.game_state.played_cards = []
                session.game_state.played_cards_history.clear()
                session.game_state.round_passes.clear()
                
                # Set the last player who played as the current player for new round
                if session.game_state.last_player_to_play is not None:
                    session.game_state.current_player_index = session.game_state.last_player_to_play
                    print(f"New round starting with Player {session.game_state.last_player_to_play} (last to play)")
                    self.broadcast_game_state_to_session(session.session_id)
                    
                    # Check if the new current player is an AI and needs automated turn
                    current_player_id = None
                    for client_id, info in session.clients.items():
                        if info['player_index'] == session.game_state.current_player_index:
                            current_player_id = client_id
                            break
                    
                    if current_player_id is None:
                        # It's an AI player, schedule their turn
                        threading.Timer(2.0, lambda: self.handle_ai_turn(session)).start()
                    
                    return

            self.next_turn(session)

    def next_turn(self, session):
        session.game_state.current_player_index = (session.game_state.current_player_index + 1) % 4

        # Skip players who passed this round only
        attempts = 0
        while (session.game_state.current_player_index in session.game_state.round_passes and
               attempts < 4):
            session.game_state.current_player_index = (session.game_state.current_player_index + 1) % 4
            attempts += 1

        self.broadcast_game_state_to_session(session.session_id)

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

            print(f"🤖 AI TURN: Player {player_index} ({current_player.name})")
            print(f"📋 Current round passes: {sorted(list(session.game_state.round_passes))}")

            played = False
            for card in current_player.hand:
                if (
                    play([card], current_player.hand, session.game_state.played_cards)
                    == 0
                ):
                    current_player.hand.remove(card)
                    session.game_state.played_cards = [card]
                    for c in session.game_state.played_cards:
                        c.selected_by = current_player.name
                    session.game_state.played_cards_history.append([card])
                    session.game_state.last_player_to_play = player_index  # Track AI play

                    # DON'T clear round passes when AI plays - only when 3 players pass
                    played = True
                    print(f"✅ AI {current_player.name} played card {card.number}")
                    break

            if not played:
                # AI passes this round
                session.game_state.round_passes.add(player_index)
                print(f"❌ AI {current_player.name} passed")
                
                # Print detailed pass information for AI
                passed_names = []
                for passed_idx in session.game_state.round_passes:
                    passed_names.append(f"{passed_idx}({session.game_state.players[passed_idx].name})")
                print(f"👥 Players who have passed: {', '.join(passed_names)}")
                print(f"🔢 Total passes this round: {len(session.game_state.round_passes)}/3")
                
                # Check if 3 players passed in this round
                if len(session.game_state.round_passes) >= 3:
                    # Clear the table and start new round with last player who played
                    session.game_state.played_cards = []
                    session.game_state.played_cards_history.clear()
                    session.game_state.round_passes.clear()
                    
                    # Set the last player who played as the current player for new round
                    if session.game_state.last_player_to_play is not None:
                        session.game_state.current_player_index = session.game_state.last_player_to_play
                        print(f"New round starting with Player {session.game_state.last_player_to_play} (last to play)")
                        
                        # Broadcast the new game state and check if it's AI's turn
                        self.broadcast_game_state_to_session(session.session_id)
                        
                        # Check if the new current player is also an AI
                        current_player_id = None
                        for client_id, info in session.clients.items():
                            if info['player_index'] == session.game_state.current_player_index:
                                current_player_id = client_id
                                break
                        
                        if current_player_id is None:
                            threading.Timer(2.0, lambda: self.handle_ai_turn(session)).start()
                        
                        return  # Don't call next_turn() - we've already set the correct player

            # Check for game end
            if len(current_player.hand) == 0:
                self.end_game(session, current_player.name)
                return

            # Only call next_turn if we didn't start a new round
            self.next_turn(session)

    def start_new_game(self, client_id):
        session = self.get_session(client_id)
        if not session:
            # For HTTP server: return {'error': 'No session found'}
            return

        with self.lock:
            if len(session.clients) == 0:
                return

            session.game_state.reset_game()
            session.status = "playing"

            redis_client.hset(f"session:{session.session_id}", "status", "playing")
            
            players_names_to_redis = ["", "", "", ""]
            for i in range(4):
                human_in_slot = False
                for client_id, client_info in session.clients.items():
                    if client_info['player_index'] == i:
                        session.game_state.players[i].name = client_info['name']
                        session.game_state.players_names[i] = client_info['name']
                        players_names_to_redis[i] = client_info['name']
                        human_in_slot = True
                        break
                
                if not human_in_slot:
                    session.game_state.players[i].name = self.ai_names[i]
                    session.game_state.players_names[i] = self.ai_names[i]
                    players_names_to_redis[i] = self.ai_names[i]
            
            redis_client.hset(f"session:{session.session_id}", "players_names_json", json.dumps(players_names_to_redis))

            deal(session.game_state.players)

            starting_player = who_starts(session.game_state.players)
            session.game_state.current_player_index = session.game_state.players.index(starting_player)

            session.game_state.game_active = True

            game_state_data = {
                'current_player_index': session.game_state.current_player_index,
                'game_active': True,
                'winner': None,
                'played_cards': [],
                'played_cards_history': [],
                'players_passed': [],
                'round_passes': [],
                'players_card_counts': [len(p.hand) for p in session.game_state.players]
            }
            
            redis_client.hset(f"session:{session.session_id}", "game_state_json", json.dumps(game_state_data))
            
            redis_client.hset(f"session:{session.session_id}", "current_player_index", session.game_state.current_player_index)

            print(f"New Capsa game started in session '{session.session_name}'!")
            print(f"Players: {[p.name for p in session.game_state.players]}")
            print(f"Starting player: {starting_player.name}")

            self.broadcast_game_state_to_session(session.session_id)

            starting_is_human = any(
                info['player_index'] == session.game_state.current_player_index
                for info in session.clients.values()
            )

            if not starting_is_human:
                threading.Timer(2.0, lambda: self.handle_ai_turn(session)).start()

            # For HTTP server: return {'success': 'Game started'}

    def end_game(self, session, winner_name):
        session.game_state.game_active = False
        session.game_state.winner = winner_name
        session.status = "finished"

        redis_client.hset(f"session:{session.session_id}", "status", "finished")
        
        redis_client.hset(f"session:{session.session_id}", "winner", winner_name)
        
        game_state_data = {
            'current_player_index': session.game_state.current_player_index,
            'game_active': False,
            'winner': winner_name,
            'played_cards': [self.card_to_dict(card) for card in session.game_state.played_cards],
            'played_cards_history': [[self.card_to_dict(card) for card in hand] for hand in session.game_state.played_cards_history],
            'players_passed': list(session.game_state.players_passed),
            'round_passes': list(session.game_state.round_passes),
            'players_card_counts': [len(p.hand) for p in session.game_state.players]
        }
        redis_client.hset(f"session:{session.session_id}", "game_state_json", json.dumps(game_state_data))
        
        game_end_time = datetime.now().isoformat()
        redis_client.hset(f"session:{session.session_id}", "game_end_time", game_end_time)
        
        redis_client.expire(f"session:{session.session_id}", 3600)

        # Broadcast game end message to all clients
        self.broadcast_message_to_session(session.session_id, {
            'command': 'GAME_END',
            'winner': winner_name,
            'game_end_time': game_end_time
        })

        print(f"Game ended in session '{session.session_name}'! Winner: {winner_name}")
        print(f"Session data will expire in 1 hour for cleanup")

        # Schedule auto restart after 5 seconds
        threading.Timer(5.0, lambda: self.auto_restart_game(session)).start()

    def auto_restart_game(self, session):
        if len(session.clients) > 0:
            session.status = "waiting"
            session.game_state.reset_game()
            
            redis_client.hset(f"session:{session.session_id}", "status", "waiting")
            
            redis_client.sadd("active_sessions", session.session_id)
            
            redis_client.hdel(f"session:{session.session_id}", "winner", "game_end_time")
            
            initial_game_state = {
                'current_player_index': 0,
                'game_active': False,
                'winner': None,
                'played_cards': [],
                'played_cards_history': [],
                'players_passed': [],
                'round_passes': [],
                'players_card_counts': [0, 0, 0, 0]
            }
            redis_client.hset(f"session:{session.session_id}", "game_state_json", json.dumps(initial_game_state))
            
            redis_client.hset(f"session:{session.session_id}", "current_player_index", 0)
            
            redis_client.persist(f"session:{session.session_id}")
            
            print(f"Session '{session.session_name}' auto-restarted and set to waiting state")
            
            self.broadcast_game_state_to_session(session.session_id)
            
            self.broadcast_message_to_session(session.session_id, {
                'command': 'GAME_RESTARTED',
                'message': 'Game has been restarted. Ready for a new game!'
            })
        else:
            print(f"Session '{session.session_name}' has no clients, cleaning up...")
            redis_client.srem("active_sessions", session.session_id)
            redis_client.delete(f"session:{session.session_id}")
            
            if session.session_id in self.sessions:
                del self.sessions[session.session_id]

    def send_to_client(self, client_id, message):
        try:
            if client_id in self.clients:
                socket_obj = self.clients[client_id]['socket']
                msg = json.dumps(message) + '\n'
                socket_obj.send(msg.encode())
        except Exception as e:
            logging.warning(f"Failed to send to {client_id}: {e}")
            self.remove_client(client_id)

    def send_to_client_direct(self, socket, message):
        try:
            msg = json.dumps(message) + '\n'
            socket.send(msg.encode())
        except Exception as e:
            logging.warning(f"Failed to send to socket: {e}")

    def broadcast_message_to_session(self, session_id, message):
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]
        msg = json.dumps(message) + '\n'
        dead_clients = []

        for client_id, client_info in session.clients.items():
            try:
                client_info['socket'].send(msg.encode())
            except Exception as e:
                logging.warning(f"Failed to broadcast to {client_id}: {e}")
                dead_clients.append(client_id)

        for client_id in dead_clients:
            self.remove_client(client_id)

    # In CapsaGameServer class
    def broadcast_game_state_to_session(self, session_id):
        session_data_from_redis = redis_client.hgetall(f"session:{session_id}")
        if not session_data_from_redis:
            logging.warning(f"Session {session_id} not found in Redis during broadcast.")
            return

        session = self.sessions.get(session_id)
        if not session:
             logging.warning(f"Attempted to broadcast for session {session_id} not locally managed by this VM.")
             return

        global_players_names = json.loads(session_data_from_redis.get('players_names_json', '["", "", "", ""]'))
        global_player_count = int(session_data_from_redis.get('player_count', 0))

        for i in range(4):
            session.game_state.players_names[i] = global_players_names[i]

        hands_data = {}
        for client_id, client_info in session.clients.items():
            player_index = client_info['player_index']
            hands_data[client_id] = [self.card_to_dict(card) for card in session.game_state.players[player_index].hand]

        played_cards_data = [self.card_to_dict(card) for card in session.game_state.played_cards]

        for client_id, client_info in session.clients.items():
            state_msg = {
                'command': 'GAME_UPDATE',
                'session_id': session_id,
                'session_name': session_data_from_redis.get('session_name'),
                'current_player_index': session.game_state.current_player_index,
                'current_player_name': session.game_state.players[session.game_state.current_player_index].name,
                'players_names': global_players_names,
                'my_hand': hands_data[client_id],
                'my_player_index': client_info['player_index'],
                'played_cards': played_cards_data,
                'players_card_counts': [len(p.hand) for p in session.game_state.players],
                'game_active': session.game_state.game_active,
                'winner': session.game_state.winner,
                'players_passed': list(session.game_state.round_passes)
            }
            self.send_to_client(client_id, state_msg)

        current_player_name = session.game_state.players[session.game_state.current_player_index].name
        print(f"Broadcasting game state to session '{session.session_name}' - Current player: {current_player_name}")

    def card_to_dict(self, card):
        return {
            'number': card.number,
            'suit': card.suit,
            'value': card.value,
            'pp_value': card.pp_value,
            'selected': getattr(card, 'selected', False)
        }