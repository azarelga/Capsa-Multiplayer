import pygame
import socket
import json
import time
import sys
import logging
from urllib.parse import urlparse
from common.game import (
    show_session_menu,
    get_session_name,
    get_creator_name,
    show_sessions_list,
    get_player_name,
    init_pygame,
    draw_game,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class ClientInterface:
    def __init__(self, server_address="http://127.0.0.1:8886"):
        self.server_address = server_address
        self.session_cookies = {}

    def make_socket(self, destination_address="localhost", port=80):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_address = (destination_address, port)
            logging.info(f"Connecting to {server_address}")
            sock.connect(server_address)
            return sock
        except Exception as e:
            logging.error(f"Socket creation error: {str(e)}")
            return None

    def send_request(self, host, port, request):
        sock = self.make_socket(host, port)
        if not sock:
            return None

        try:
            sock.sendall(request)
            logging.info("HTTP request sent")

            response = b""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data
                
                if b"\r\n\r\n" in response:
                    headers_part = response.split(b"\r\n\r\n")[0]
                    if b"content-length:" in headers_part.lower():
                        for line in headers_part.split(b"\r\n"):
                            if line.lower().startswith(b"content-length:"):
                                content_length = int(line.split(b":")[1].strip())
                                body_received = len(response.split(b"\r\n\r\n", 1)[1])
                                while body_received < content_length:
                                    more_data = sock.recv(4096)
                                    if not more_data:
                                        break
                                    response += more_data
                                    body_received = len(response.split(b"\r\n\r\n", 1)[1])
                                break
                    break

            sock.close()
            return response

        except Exception as e:
            logging.error(f"Request sending error: {str(e)}")
            return None

    def send_command(self, command_str="", data=None, method="GET"):
        parsed = urlparse(self.server_address)
        
        if ':' in parsed.netloc:
            host = parsed.netloc.split(':')[0]
            port = int(parsed.netloc.split(':')[1])
        else:
            host = parsed.netloc
            port = 8886

        if method == "GET":
            if command_str.startswith("/"):
                path = command_str
            else:
                path = f"/{command_str}"
                
            request_headers = {
                "Host": f"{host}:{port}",
                "User-Agent": "Python-CapsaClient/1.0",
                "Accept": "application/json",
                "Connection": "close",
            }

            request = f"GET {path} HTTP/1.1\r\n"
            for key, value in request_headers.items():
                request += f"{key}: {value}\r\n"
            request += "\r\n"
            request = request.encode("utf-8")

        elif method == "POST":
            if command_str.startswith("/"):
                path = command_str
            else:
                path = f"/{command_str}"
            
            if data is None:
                data = ""
            if isinstance(data, dict):
                data = json.dumps(data)

            request_headers = {
                "Host": f"{host}:{port}",
                "User-Agent": "Python-CapsaClient/1.0",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Content-Length": str(len(data)),
                "Connection": "close",
            }

            request = f"POST {path} HTTP/1.1\r\n"
            for key, value in request_headers.items():
                request += f"{key}: {value}\r\n"
            request = request.encode()
            request += "\r\n".encode()
            if type(data) is not bytes:
                data = data.encode()
            request += data

        logging.info(f"{method} request to {self.server_address}{path}")
        response = self.send_request(host, port, request)
        
        if response:
            response_str = response.decode("utf-8", errors="ignore")
            
            if "\r\n\r\n" in response_str:
                headers, body = response_str.split("\r\n\r\n", 1)
                
                status_line = headers.split("\r\n")[0]
                if "200 OK" in status_line or "201 Created" in status_line:
                    try:
                        hasil = json.loads(body) if body.strip() else {}
                        
                        if isinstance(hasil, list):
                            return {'status': 'OK', 'data': hasil}
                        elif isinstance(hasil, dict):
                            hasil['status'] = 'OK'
                            return hasil
                        else:
                            return {'status': 'OK', 'data': hasil}
                            
                    except json.JSONDecodeError:
                        return {'status': 'OK', 'message': 'Success'}
                else:
                    try:
                        error_data = json.loads(body) if body.strip() else {}
                        if isinstance(error_data, dict):
                            error_data['status'] = 'ERROR'
                            return error_data
                        else:
                            return {'status': 'ERROR', 'data': error_data}
                    except json.JSONDecodeError:
                        return {'status': 'ERROR', 'message': status_line}
            else:
                return {'status': 'ERROR', 'message': 'Invalid HTTP response'}
        else:
            return {'status': 'ERROR', 'message': 'Connection error'}

    def get_sessions(self):
        command_str = "sessions"
        hasil = self.send_command(command_str, method="GET")
        if hasil['status'] == 'OK':
            if 'data' in hasil:
                return hasil['data']
            else:
                sessions = [key for key in hasil.keys() if key != 'status']
                if sessions:
                    return [hasil[key] for key in sessions if isinstance(hasil[key], dict)]
                else:
                    return []
        return None

    def create_session(self, session_name, creator_name):
        command_str = "sessions"
        data = {"session_name": session_name, "creator_name": creator_name}
        hasil = self.send_command(command_str, data, method="POST")
        if hasil['status'] == 'OK':
            if 'data' in hasil:
                return hasil['data']
            return hasil
        return False

    def join_session(self, session_id, player_name):
        command_str = f"sessions/{session_id}/join"
        data = {"player_name": player_name}
        hasil = self.send_command(command_str, data, method="POST")
        if hasil['status'] == 'OK':
            if 'data' in hasil:
                return hasil['data']
            return hasil
        return False

    def start_game(self, session_id):
        command_str = f"sessions/{session_id}/start"
        hasil = self.send_command(command_str, {}, method="POST")
        if hasil['status'] == 'OK':
            return True
        return False

    def get_game_state(self, session_id, player_name):
        command_str = f"sessions/{session_id}?player_name={player_name}"
        hasil = self.send_command(command_str, method="GET")
        if hasil['status'] == 'OK':
            if 'data' in hasil:
                return hasil['data']
            return hasil
        return False

    def play_cards(self, session_id, player_name, card_indices):
        command_str = f"sessions/{session_id}/play"
        data = {"player_name": player_name, "cards": card_indices}
        hasil = self.send_command(command_str, data, method="POST")
        return hasil

    def pass_turn(self, session_id, player_name):
        command_str = f"sessions/{session_id}/pass"
        data = {"player_name": player_name}
        hasil = self.send_command(command_str, data, method="POST")
        return hasil


class CapsaClient:
    def __init__(self, server_address="http://127.0.0.1:8886"):
        self.server_address = server_address
        self.session_id = None
        self.session_name = None
        self.player_name = None
        self.player_index = -1
        self.game_data = self._get_default_game_data()
        self.connected = False
        self.message = ""
        self.message_timer = 0
        self.selected_cards = []
        self.client_interface = ClientInterface(server_address)

    def _get_default_game_data(self):
        return {
            "players_names": [],
            "players_card_counts": [],
            "my_hand": [],
            "played_cards": [],
            "current_player_index": -1,
            "current_player_name": "N/A",
            "game_active": False,
            "winner": None,
            "players_passed": [],
            "my_player_index": -1,
        }

    def get_sessions(self):
        return self.client_interface.get_sessions()

    def create_session(self, session_name, creator_name):
        hasil = self.client_interface.create_session(session_name, creator_name)
        if hasil and hasil != False:
            self.session_id = hasil.get("session_id")
            self.session_name = session_name
            self.player_name = creator_name
            self.connected = True
            return True
        return False

    def join_session(self, session_id, player_name):
        hasil = self.client_interface.join_session(session_id, player_name)
        if hasil and hasil != False:
            self.session_id = session_id
            self.player_name = player_name
            self.session_name = hasil.get("session_name")
            self.connected = True
            return True
        return False

    def start_game(self):
        if not self.session_id:
            return False
        return self.client_interface.start_game(self.session_id)

    def get_game_state(self):
        if not self.session_id or not self.player_name:
            return
        
        hasil = self.client_interface.get_game_state(self.session_id, self.player_name)
        if hasil and hasil != False:
            new_game_data = self._get_default_game_data()
            game_state = {k: v for k, v in hasil.items() if k != 'status'}
            new_game_data.update(game_state)
            self.game_data = new_game_data
            self.player_index = self.game_data.get("my_player_index", -1)
        else:
            self.connected = False
            self.game_data = self._get_default_game_data()

    def play_cards(self, card_indices):
        if not self.session_id or not self.player_name:
            return
        
        hasil = self.client_interface.play_cards(self.session_id, self.player_name, card_indices)
        
        if hasil['status'] != 'OK':
            error_msg = hasil.get("error", hasil.get("message", "Invalid move"))
            self.show_message(error_msg, 2)
        else:
            self.selected_cards = []
            if "winner_notification" in hasil:
                self.show_message(hasil["winner_notification"], 5)

    def pass_turn(self):
        if not self.session_id or not self.player_name:
            return
        
        hasil = self.client_interface.pass_turn(self.session_id, self.player_name)
        
        if hasil['status'] != 'OK':
            error_msg = hasil.get("error", hasil.get("message", "Cannot pass"))
            self.show_message(error_msg, 2)

    def show_message(self, text, duration=3):
        self.message = text
        self.message_timer = duration * 60


def main():
    server_address = "http://127.0.0.1:8886"
    client = CapsaClient(server_address)

    print("--- Capsa Banting Client ---")
    print("Connecting to server...")
    sessions = client.get_sessions()
    if sessions is None:
        print("Could not connect to the server. Please ensure it is running.")
        return
    print("Connection successful.")

    while not client.connected:
        choice = show_session_menu()

        if choice == 1:
            session_name = get_session_name()
            creator_name = get_creator_name()
            if client.create_session(session_name, creator_name):
                print(f"Session '{session_name}' created. Waiting for other players...")
                break
            else:
                print("Could not create session. Please try again.")
                
        elif choice == 2:
            sessions = client.get_sessions()
            if sessions is None:
                print("Could not connect to the server.")
                continue
            if not sessions:
                print("No sessions available. Check back later or create a new one.")
                continue

            session_id = show_sessions_list(sessions)
            if session_id:
                player_name = get_player_name()
                if not client.join_session(session_id, player_name):
                    print("Failed to join session. The session might be full or already started.")
                else:
                    print(f"Joined session '{client.session_name}'. Waiting for game to start...")
                    break

        elif choice == 3:
            print("Goodbye!")
            return

    print("Starting game UI...")
    screen, clock, WIDTH, HEIGHT, FPS = init_pygame()
    running = True
    card_rects, button_rects = [], []
    last_update_time = 0
    
    while running:
        is_game_active = client.game_data.get("game_active", False)
        now = time.time()
        update_interval = 0.5 if is_game_active else 3.0

        if now - last_update_time > update_interval:
            client.get_game_state()
            last_update_time = now

        if not client.connected:
            print("Lost connection to server.")
            running = False
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                
                if client.game_data.get("my_hand"):
                    card_selected = False
                    for rect, card_data in card_rects:
                        if rect.collidepoint(event.pos) and not card_selected:
                            card_number = card_data["number"]
                            for i, c in enumerate(client.game_data["my_hand"]):
                                if c["number"] == card_number:
                                    if i in client.selected_cards:
                                        client.selected_cards.remove(i)
                                    else:
                                        client.selected_cards.append(i)
                                    client.selected_cards.sort()
                                    card_selected = True
                                    break
                            if card_selected:
                                break

                for name, rect in button_rects:
                    if rect.collidepoint(event.pos):
                        if name == "PLAY":
                            if client.selected_cards:
                                client.play_cards(client.selected_cards)
                            else:
                                client.show_message("Select cards to play", 2)
                        elif name == "PASS":
                            client.pass_turn()
                        elif name == "START":
                            client.start_game()
                        break

        card_rects, button_rects = draw_game(screen, client, WIDTH, HEIGHT)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    print("Game has been closed.")


if __name__ == "__main__":
    main()