import sys
import os.path
import uuid
import json
import threading
import time
import logging
from glob import glob
from datetime import datetime
from urllib.parse import urlparse, parse_qs

# Import game server components
from server import CapsaGameServer, GameSession


class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.types = {}
        self.types[".pdf"] = "application/pdf"
        self.types[".jpg"] = "image/jpeg"
        self.types[".txt"] = "text/plain"
        self.types[".html"] = "text/html"
        self.types[".json"] = "application/json"

        # Initialize game server
        self.game_server = HTTPCapsaGameServer()  # Use HTTP-specific version
        self.running = True

        # Start cleanup thread
        self.cleanup_thread = threading.Thread(
            target=self.cleanup_inactive_clients, daemon=True
        )
        self.cleanup_thread.start()

    def cleanup_inactive_clients(self):
        """Background thread to clean up inactive clients"""
        while self.running:
            try:
                self.game_server.cleanup_inactive_clients()
                time.sleep(10)
            except Exception as e:
                logging.error(f"Cleanup error: {e}")

    def response(self, kode=404, message="Not Found", messagebody=bytes(), headers={}):
        tanggal = datetime.now().strftime("%c")
        resp = []
        resp.append("HTTP/1.0 {} {}\r\n".format(kode, message))
        resp.append("Date: {}\r\n".format(tanggal))
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")
        resp.append("Content-Length: {}\r\n".format(len(messagebody)))

        # Add CORS headers by default
        resp.append("Access-Control-Allow-Origin: *\r\n")
        resp.append("Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n")
        resp.append("Access-Control-Allow-Headers: Content-Type\r\n")

        for kk in headers:
            resp.append("{}:{}\r\n".format(kk, headers[kk]))
        resp.append("\r\n")

        response_headers = ""
        for i in resp:
            response_headers = "{}{}".format(response_headers, i)

        if type(messagebody) is not bytes:
            messagebody = messagebody.encode()

        response = response_headers.encode() + messagebody
        return response

    def json_response(self, data, status=200, message="OK"):
        """Helper method to create JSON responses"""
        json_data = json.dumps(data)
        headers = {"Content-Type": "application/json"}
        return self.response(status, message, json_data, headers)

    def proses(self, data):
        requests = data.split("\r\n")
        baris = requests[0]

        # Parse headers like reference.py
        all_headers = [n for n in requests[1:] if n != ""]

        # Parse request body for POST requests
        request_body = ""
        if "\r\n\r\n" in data:
            request_body = data.split("\r\n\r\n", 1)[1]

        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            if method == "GET":
                object_address = j[1].strip()
                return self.http_get(object_address, all_headers)
            elif method == "POST":
                object_address = j[1].strip()
                return self.http_post(object_address, all_headers, request_body)
            elif method == "OPTIONS":
                return self.http_options()
            else:
                return self.response(400, "Bad Request", "", {})
        except IndexError:
            return self.response(400, "Bad Request", "", {})

    def http_options(self):
        """Handle CORS preflight requests"""
        return self.response(200, "OK", "", {})

    def http_get(self, object_address, headers):
        try:
            parsed_url = urlparse(object_address)
            path = parsed_url.path
            query_params = parse_qs(parsed_url.query)

            # Extract client_id from query params
            client_id = query_params.get("client_id", [""])[0]

            if path == "/":
                return self.response(
                    200,
                    "OK",
                    "Capsa Multiplayer Server - Use /api/ endpoints for game functionality",
                )

            elif path == "/video":
                return self.response(
                    302, "Found", "", {"location": "https://youtu.be/katoxpnTf04"}
                )

            elif path == "/santai":
                return self.response(200, "OK", "santai saja")

            elif path == "/api/ping":
                if client_id and client_id in self.game_server.clients:
                    self.game_server.update_client_activity(client_id)
                return self.json_response({"status": "pong"})

            elif path == "/api/register":
                # Register new client via GET
                client_name = query_params.get(
                    "client_name", [f"Player_{str(uuid.uuid4())[:8]}"]
                )[0]
                new_client_id = str(uuid.uuid4())
                self.game_server.add_client(new_client_id, client_name, None)
                return self.json_response(
                    {"client_id": new_client_id, "client_name": client_name}
                )

            elif path == "/api/sessions":
                # List all sessions via GET
                if client_id and client_id in self.game_server.clients:
                    self.game_server.update_client_activity(client_id)
                    sessions = [
                        session.to_dict()
                        for session in self.game_server.sessions.values()
                    ]
                    return self.json_response(
                        {"command": "SESSION_MENU", "sessions": sessions}
                    )
                else:
                    return self.json_response(
                        {"error": "Invalid client_id"}, 400, "Bad Request"
                    )

            elif path == "/api/game_state":
                # Get current game state via GET
                if not client_id:
                    return self.json_response(
                        {"error": "client_id required"}, 400, "Bad Request"
                    )

                if client_id not in self.game_server.clients:
                    return self.json_response(
                        {"error": "Client not found"}, 404, "Not Found"
                    )

                self.game_server.update_client_activity(client_id)
                game_state = self.game_server.get_game_state(client_id)
                return self.json_response(game_state)

            elif path == "/api/session_info":
                # Get session information via GET
                if not client_id:
                    return self.json_response(
                        {"error": "client_id required"}, 400, "Bad Request"
                    )

                if client_id not in self.game_server.clients:
                    return self.json_response(
                        {"error": "Client not found"}, 404, "Not Found"
                    )

                self.game_server.update_client_activity(client_id)
                client_info = self.game_server.clients[client_id]
                session_id = client_info.get("session_id")

                if not session_id:
                    return self.json_response({"error": "Not in a session"})

                session = self.game_server.sessions.get(session_id)
                if not session:
                    return self.json_response({"error": "Session not found"})

                return self.json_response(
                    {
                        "session_id": session_id,
                        "session_name": session.session_name,
                        "player_index": client_info.get("player_index", -1),
                        "player_name": client_info.get("name", ""),
                        "is_creator": client_info.get("is_creator", False),
                    }
                )

            else:
                # Handle file requests like reference.py
                files = glob("./*")
                thedir = "./"
                object_address = path[1:]  # Remove leading slash

                if thedir + object_address not in files:
                    return self.response(404, "Not Found", "")

                fp = open(thedir + object_address, "rb")
                isi = fp.read()
                fp.close()

                fext = os.path.splitext(thedir + object_address)[1]
                content_type = self.types.get(fext, "application/octet-stream")

                headers = {"Content-type": content_type}
                return self.response(200, "OK", isi, headers)

        except Exception as e:
            logging.error(f"GET error: {e}")
            return self.json_response({"error": str(e)}, 500, "Internal Server Error")

    def http_post(self, object_address, headers, request_body):
        try:
            parsed_url = urlparse(object_address)
            path = parsed_url.path

            # Parse JSON data from request body
            try:
                data = json.loads(request_body) if request_body else {}
            except json.JSONDecodeError:
                return self.json_response({"error": "Invalid JSON"}, 400, "Bad Request")

            if path == "/api/register":
                # Register new client via POST
                client_name = data.get("client_name", f"Player_{str(uuid.uuid4())[:8]}")
                new_client_id = str(uuid.uuid4())
                self.game_server.add_client(new_client_id, client_name, None)
                return self.json_response(
                    {"client_id": new_client_id, "client_name": client_name}
                )

            elif path == "/api/game" or path == "/api/command":
                # Handle game commands via POST
                client_id = data.get("client_id")
                if not client_id:
                    return self.json_response(
                        {"error": "client_id required"}, 400, "Bad Request"
                    )

                # Add client if not exists
                if client_id not in self.game_server.clients:
                    client_name = data.get("client_name", f"Player_{client_id[:8]}")
                    self.game_server.add_client(client_id, client_name, None)

                # Update client activity
                self.game_server.update_client_activity(client_id)

                # Handle game commands
                response = self.game_server.handle_command(client_id, data)
                return self.json_response(response)

            elif path == "/api/create_session":
                # Create session via POST
                client_id = data.get("client_id")
                if not client_id:
                    return self.json_response(
                        {"error": "client_id required"}, 400, "Bad Request"
                    )

                if client_id not in self.game_server.clients:
                    return self.json_response(
                        {"error": "Client not found"}, 404, "Not Found"
                    )

                session_name = data.get("session_name", f"Session_{client_id[:8]}")
                creator_name = data.get("creator_name", f"Player_{client_id[:8]}")

                self.game_server.update_client_activity(client_id)
                self.game_server.create_session(client_id, session_name, creator_name)

                return self.json_response(
                    {
                        "success": "Session created",
                        "session_id": self.game_server.clients[client_id].get(
                            "session_id"
                        ),
                    }
                )

            elif path == "/api/join_session":
                # Join session via POST
                client_id = data.get("client_id")
                session_id = data.get("session_id")

                if not client_id or not session_id:
                    return self.json_response(
                        {"error": "client_id and session_id required"},
                        400,
                        "Bad Request",
                    )

                if client_id not in self.game_server.clients:
                    return self.json_response(
                        {"error": "Client not found"}, 404, "Not Found"
                    )

                player_name = data.get("player_name", f"Player_{client_id[:8]}")

                self.game_server.update_client_activity(client_id)
                result = self.game_server.join_session(
                    client_id, session_id, player_name
                )

                if result:
                    return self.json_response({"success": "Joined session"})
                else:
                    return self.json_response({"error": "Failed to join session"})

            else:
                return self.json_response(
                    {"error": "Endpoint not found"}, 404, "Not Found"
                )

        except Exception as e:
            logging.error(f"POST error: {e}")
            return self.json_response({"error": str(e)}, 500, "Internal Server Error")


# Extend CapsaGameServer for HTTP-specific functionality
class HTTPCapsaGameServer(CapsaGameServer):
    def __init__(self):
        super().__init__()
        self.client_activity = {}  # Track last activity time

    def add_client(self, client_id, client_name=None, socket=None):
        """Add client for HTTP (no socket)"""
        with self.lock:
            self.clients[client_id] = {
                "name": client_name or f"Player_{client_id[:8]}",
                "session_id": None,
                "player_index": -1,
                "socket": None,  # HTTP clients don't have persistent sockets
                "last_activity": datetime.now(),
            }
            self.client_activity[client_id] = datetime.now()
            print(
                f"HTTP Client {client_name or client_id[:8]} ({client_id[:8]}) connected"
            )

    def update_client_activity(self, client_id):
        """Update client's last activity time"""
        if client_id in self.clients:
            self.client_activity[client_id] = datetime.now()
            self.clients[client_id]["last_activity"] = datetime.now()

    def cleanup_inactive_clients(self):
        """Remove clients that haven't been active for too long"""
        current_time = datetime.now()
        inactive_clients = []

        with self.lock:
            for client_id, last_activity in self.client_activity.items():
                if (
                    current_time - last_activity
                ).total_seconds() > 300:  # 5 minutes timeout
                    inactive_clients.append(client_id)

        for client_id in inactive_clients:
            print(f"Removing inactive HTTP client: {client_id[:8]}")
            self.remove_client(client_id)

    def send_to_client(self, client_id, message):
        """HTTP doesn't send real-time messages, just return the message"""
        return message

    def send_to_client_direct(self, socket, message):
        """HTTP doesn't use direct socket sending"""
        pass

    def broadcast_message_to_session(self, session_id, message):
        """HTTP doesn't broadcast real-time, messages are retrieved via polling"""
        pass

    def get_session(self, client_id):
        """Get session for a client"""
        client_info = self.clients.get(client_id)
        if not client_info:
            return None

        session_id = client_info.get("session_id")
        if not session_id:
            return None

        return self.sessions.get(session_id)

    def get_game_state(self, client_id):
        """Get current game state for HTTP polling"""
        session = self.get_session(client_id)
        if not session:
            return {"error": "Not in a session"}

        client_info = self.clients.get(client_id)
        if not client_info:
            return {"error": "Client not found"}

        player_index = client_info.get("player_index", -1)

        # Get player's hand
        my_hand = []
        if 0 <= player_index < len(session.game_state.players):
            my_hand = [
                self.card_to_dict(card)
                for card in session.game_state.players[player_index].hand
            ]

        # Get current player name
        current_player_name = ""
        if (
            0
            <= session.game_state.current_player_index
            < len(session.game_state.players)
            and session.game_state.players[session.game_state.current_player_index]
        ):
            current_player_name = session.game_state.players[
                session.game_state.current_player_index
            ].name

        return {
            "command": "GAME_UPDATE",
            "session_id": session.session_id,
            "session_name": session.session_name,
            "current_player_index": session.game_state.current_player_index,
            "current_player_name": current_player_name,
            "players_names": session.game_state.players_names,
            "my_hand": my_hand,
            "my_player_index": player_index,
            "played_cards": [
                self.card_to_dict(card) for card in session.game_state.played_cards
            ],
            "players_card_counts": [len(p.hand) for p in session.game_state.players],
            "game_active": session.game_state.game_active,
            "winner": session.game_state.winner,
            "players_passed": list(session.game_state.round_passes),
        }

    def card_to_dict(self, card):
        return {
            "number": card.number,
            "suit": card.suit,
            "value": card.value,
            "pp_value": card.pp_value,
            "selected": getattr(card, "selected", False),
        }

    def send_session_menu(self, client_id):
        """Override to return data instead of sending"""
        sessions_list = []
        for session in self.sessions.values():
            sessions_list.append(session.to_dict())

        return {"command": "SESSION_MENU", "sessions": sessions_list}

    def handle_command(self, client_id, command):
        """Handle HTTP game commands and return responses"""
        cmd_type = command.get("command")

        try:
            if cmd_type == "CREATE_SESSION":
                session_name = command.get("session_name", f"Session_{client_id[:8]}")
                creator_name = command.get("creator_name", f"Player_{client_id[:8]}")
                self.create_session(client_id, session_name, creator_name)
                return {
                    "success": "Session created",
                    "session_id": self.clients[client_id].get("session_id"),
                }

            elif cmd_type == "JOIN_SESSION":
                session_id = command.get("session_id")
                player_name = command.get("player_name", f"Player_{client_id[:8]}")
                result = self.join_session(client_id, session_id, player_name)
                if result:
                    return {"success": "Joined session"}
                else:
                    return {"error": "Failed to join session"}

            elif cmd_type == "LIST_SESSIONS":
                sessions = [session.to_dict() for session in self.sessions.values()]
                return {"command": "SESSION_MENU", "sessions": sessions}

            elif cmd_type == "GET_GAME_STATE":
                return self.get_game_state(client_id)

            elif cmd_type == "PLAY_CARDS":
                card_numbers = command.get("cards", [])
                result = self.handle_play_cards(client_id, card_numbers)
                if result:
                    return {"success": "Cards played"}
                else:
                    return {"error": "Invalid card play"}

            elif cmd_type == "PASS_TURN":
                result = self.handle_pass_turn(client_id)
                if result:
                    return {"success": "Turn passed"}
                else:
                    return {"error": "Cannot pass turn"}

            elif cmd_type == "START_GAME":
                self.start_new_game(client_id)
                return {"success": "Game started"}

            else:
                return {"error": f"Unknown command: {cmd_type}"}

        except Exception as e:
            logging.error(f"Command handling error: {e}")
            return {"error": str(e)}


if __name__ == "__main__":
    httpserver = HttpServer()

    # Test basic functionality
    d = httpserver.proses("GET / HTTP/1.0\r\n\r\n")
    print(d.decode())

    # Test game API
    test_data = json.dumps({"command": "LIST_SESSIONS"})
    post_request = f"POST /api/game HTTP/1.0\r\nContent-Length: {len(test_data)}\r\n\r\n{test_data}"
    d = httpserver.proses(post_request)
    print(d.decode())
