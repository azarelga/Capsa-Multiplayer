import sys
import os.path
import uuid
from glob import glob
from datetime import datetime
import json
from game import (
    GameState,
    Player,
    Card,
    deck,
    deal,
    who_starts,
    value_checker,
    quantity_checker,
    play,
)


class GameSession:
    def __init__(self, session_name, creator_name):
        self.session_id = str(uuid.uuid4())
        self.session_name = session_name
        self.creator_name = creator_name
        self.players = [Player(creator_name)]
        self.game_state = GameState.MENU
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.last_played_cards = []
        self.current_player_index = 0
        self.last_player_to_play = None
        self.passed_players = []
        self.winners = []

    def add_player(self, player_name):
        if len(self.players) < 4:
            self.players.append(Player(player_name))
            return True
        return False

    def start_game(self):
        # Fill with AI players if there are 2 or 3 players
        num_players = len(self.players)
        if 1 < num_players < 4:
            for i in range(num_players, 4):
                self.add_player(f"AI Player {i - num_players + 1}")

        if len(self.players) > 1 and self.game_state == GameState.MENU:
            self.game_state = GameState.PLAYING
            deal(self.players)

            starter = who_starts(self.players)
            if starter:
                self.current_player_index = self.players.index(starter)
            else:
                # Fallback if 3 of diamonds is not found (should not happen with a full deck)
                self.current_player_index = 0

            self.last_player_to_play = self.current_player_index
            return True
        return False

    def get_player(self, player_name):
        for p in self.players:
            if p.name == player_name:
                return p
        return None

    def get_player_index(self, player_name):
        for i, p in enumerate(self.players):
            if p.name == player_name:
                return i
        return -1

    def to_json(self):
        return {
            "session_id": self.session_id,
            "session_name": self.session_name,
            "creator_name": self.creator_name,
            "players": [p.name for p in self.players],
            "player_count": len(self.players),
            "game_state": self.game_state.name,
            "created_at": self.created_at,
        }

    def get_game_state_for_player(self, player_name):
        player = self.get_player(player_name)
        player_index = self.get_player_index(player_name)

        if not player:
            return {"error": "Player not in session"}

        return {
            "session_name": self.session_name,
            "players_names": [p.name for p in self.players],
            "my_hand": [
                {
                    "number": c.number,
                    "suit": c.suit,
                    "value": c.value,
                    "pp_value": c.pp_value,
                }
                for c in sorted(player.hand, key=lambda x: x.number)
            ],
            "played_cards": [
                {
                    "number": c.number,
                    "suit": c.suit,
                    "value": c.value,
                    "pp_value": c.pp_value,
                }
                for c in self.last_played_cards
            ],
            "current_player_name": self.players[self.current_player_index].name,
            "current_player_index": self.current_player_index,
            "my_player_index": player_index,
            "game_active": self.game_state == GameState.PLAYING,
            "game_over": self.game_state == GameState.GAME_OVER,
            "winners": self.winners,
            "players_passed": self.passed_players,
            "player_hand_counts": {p.name: len(p.hand) for p in self.players},
        }


class HttpServer:
    def __init__(self):
        self.sessions = {}
        self.game_sessions = {}  # session_id -> GameSession
        self.types = {}
        self.types[".pdf"] = "application/pdf"
        self.types[".jpg"] = "image/jpeg"
        self.types[".txt"] = "text/plain"
        self.types[".html"] = "text/html"

    def response(
        self, kode=404, message="Not Found", messagebody: any = b"", headers={}
    ):
        tanggal = datetime.now().strftime("%c")
        resp = []
        resp.append(f"HTTP/1.0 {kode} {message}\r\n")
        resp.append(f"Date: {tanggal}\r\n")
        resp.append("Connection: close\r\n")
        resp.append("Server: myserver/1.0\r\n")

        if isinstance(messagebody, dict) or isinstance(messagebody, list):
            messagebody = json.dumps(messagebody)
            headers["Content-type"] = "application/json"

        if not isinstance(messagebody, bytes):
            messagebody = str(messagebody).encode()

        resp.append(f"Content-Length: {len(messagebody)}\r\n")
        for kk in headers:
            resp.append(f"{kk}:{headers[kk]}\r\n")
        resp.append("\r\n")

        response_headers = "".join(resp)

        response = response_headers.encode() + messagebody
        return response

    def proses(self, data):
        requests = data.split("\r\n")
        baris = requests[0]
        all_headers = [n for n in requests[1:] if n != ""]

        content_length = 0
        for h in all_headers:
            if h.lower().startswith("content-length:"):
                try:
                    content_length = int(h.split(":")[1].strip())
                except (ValueError, IndexError):
                    content_length = 0

        body = ""
        if content_length > 0 and "\r\n\r\n" in data:
            body = data.split("\r\n\r\n", 1)[1]

        j = baris.split(" ")
        try:
            method = j[0].upper().strip()
            if method == "GET":
                object_address = j[1].strip()
                return self.http_get(object_address, all_headers)
            if method == "POST":
                object_address = j[1].strip()
                return self.http_post(object_address, all_headers, body)
            else:
                return self.response(400, "Bad Request", "", {})
        except IndexError:
            return self.response(400, "Bad Request", "", {})

    def http_get(self, object_address, headers):
        if object_address == "/sessions":
            return self.response(
                200, "OK", [s.to_json() for s in self.game_sessions.values()]
            )

        if object_address.startswith("/sessions/"):
            parts = object_address.split("/")
            if len(parts) < 3:
                return self.response(404, "Not Found", "")
            session_id = parts[2]
            player_name = None
            # check for player_name in query params
            if "?" in session_id:
                session_id, query = session_id.split("?", 1)
                params = dict(p.split("=") for p in query.split("&"))
                player_name = params.get("player_name")

            session = self.game_sessions.get(session_id)
            if session and player_name:
                return self.response(
                    200, "OK", session.get_game_state_for_player(player_name)
                )
            return self.response(404, "Not Found", "")

        files = glob("./*")
        # print(files)
        thedir = "./"
        if object_address == "/":
            return self.response(200, "OK", "Ini Adalah web Server percobaan", dict())

        if object_address == "/video":
            return self.response(
                302, "Found", "", dict(location="https://youtu.be/katoxpnTf04")
            )
        if object_address == "/santai":
            return self.response(200, "OK", "santai saja", dict())

        object_address = object_address[1:]
        if thedir + object_address not in files:
            return self.response(404, "Not Found", "", {})
        fp = open(
            thedir + object_address, "rb"
        )  # rb => artinya adalah read dalam bentuk binary
        # harus membaca dalam bentuk byte dan BINARY
        isi = fp.read()

        fext = os.path.splitext(thedir + object_address)[1]
        content_type = self.types.get(fext, "application/octet-stream")

        headers = {}
        headers["Content-type"] = content_type

        return self.response(200, "OK", isi, headers)

    def http_post(self, object_address, headers, body):
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        if object_address == "/sessions":
            session_name = data.get("session_name")
            creator_name = data.get("creator_name")
            if session_name and creator_name:
                new_session = GameSession(session_name, creator_name)
                self.game_sessions[new_session.session_id] = new_session
                return self.response(201, "Created", new_session.to_json())
            return self.response(
                400,
                "Bad Request",
                {"error": "session_name and creator_name are required"},
            )

        if object_address.startswith("/sessions/") and object_address.endswith("/join"):
            session_id = object_address.split("/")[2]
            session = self.game_sessions.get(session_id)
            player_name = data.get("player_name")
            if session and player_name:
                if session.add_player(player_name):
                    return self.response(200, "OK", session.to_json())
                else:
                    return self.response(
                        400, "Bad Request", {"error": "Session is full"}
                    )
            return self.response(404, "Not Found", "")

        if object_address.startswith("/sessions/") and object_address.endswith(
            "/start"
        ):
            session_id = object_address.split("/")[2]
            session = self.game_sessions.get(session_id)
            if session:
                if session.start_game():
                    return self.response(200, "OK", {"message": "Game started"})
                else:
                    return self.response(
                        400, "Bad Request", {"error": "Game could not be started"}
                    )
            return self.response(404, "Not Found", "")

        if object_address.startswith("/sessions/") and object_address.endswith("/play"):
            session_id = object_address.split("/")[2]
            session = self.game_sessions.get(session_id)
            player_name = data.get("player_name")
            card_indices = data.get("cards", [])

            if not isinstance(card_indices, list) or not all(
                isinstance(x, int) for x in card_indices
            ):
                return self.response(400, "Bad Request", {"error": "Invalid card data"})

            if session and player_name is not None and card_indices is not None:
                player = session.get_player(player_name)
                player_index = session.get_player_index(player_name)

                if not player:
                    return self.response(
                        404, "Not Found", {"error": "Player not found"}
                    )

                if player_index != session.current_player_index:
                    return self.response(403, "Forbidden", {"error": "Not your turn"})

                try:
                    played_cards = [player.hand[i] for i in card_indices]
                except IndexError:
                    return self.response(
                        400, "Bad Request", {"error": "Invalid card index"}
                    )

                # Basic validation
                if not quantity_checker(
                    played_cards, session.last_played_cards
                ) or not value_checker(played_cards, session.last_played_cards):
                    return self.response(400, "Bad Request", {"error": "Invalid move"})

                # First turn validation
                if (
                    session.last_player_to_play == session.current_player_index
                    and not any(c.number == 0 for c in played_cards)
                    and any(c.number == 0 for c in player.hand)
                ):
                    return self.response(
                        400,
                        "Bad Request",
                        {"error": "You must play the 3 of diamonds on the first turn."},
                    )

                play(played_cards, player.hand, session.last_played_cards)
                session.last_played_cards = played_cards
                session.last_player_to_play = player_index
                session.passed_players = []

                if len(player.hand) == 0:
                    session.winners.append(player.name)
                    if len(session.winners) >= len(session.players) - 1:
                        session.game_state = GameState.GAME_OVER

                session.current_player_index = (session.current_player_index + 1) % len(
                    session.players
                )
                while (
                    session.players[session.current_player_index].name
                    in session.winners
                ):
                    session.current_player_index = (
                        session.current_player_index + 1
                    ) % len(session.players)

                return self.response(200, "OK", {"message": "Move successful"})

            return self.response(404, "Not Found", "")

        if object_address.startswith("/sessions/") and object_address.endswith("/pass"):
            session_id = object_address.split("/")[2]
            session = self.game_sessions.get(session_id)
            player_name = data.get("player_name")

            if session and player_name:
                player_index = session.get_player_index(player_name)
                if player_index != session.current_player_index:
                    return self.response(403, "Forbidden", {"error": "Not your turn"})

                if session.last_player_to_play == session.current_player_index:
                    return self.response(
                        400,
                        "Bad Request",
                        {"error": "You cannot pass, you must play a card."},
                    )

                session.passed_players.append(player_name)
                session.current_player_index = (session.current_player_index + 1) % len(
                    session.players
                )
                while (
                    session.players[session.current_player_index].name
                    in session.winners
                ):
                    session.current_player_index = (
                        session.current_player_index + 1
                    ) % len(session.players)

                # If all other active players passed, the last player to play goes again
                active_players = [
                    p.name for p in session.players if p.name not in session.winners
                ]
                if all(
                    p in session.passed_players
                    for p in active_players
                    if p != session.players[session.last_player_to_play].name
                ):
                    session.current_player_index = session.last_player_to_play
                    session.last_played_cards = []
                    session.passed_players = []

                return self.response(200, "OK", {"message": "Pass successful"})

            return self.response(404, "Not Found", "")

        return self.response(404, "Not Found", "")


# >>> import os.path
# >>> ext = os.path.splitext('/ak/52.png')

if __name__ == "__main__":
    httpserver = HttpServer()
    d = httpserver.proses("GET testing.txt HTTP/1.0")
    print(d)
    d = httpserver.proses("GET donalbebek.jpg HTTP/1.0")
    print(d)
    # d = httpserver.http_get('testing2.txt',{})
    # print(d)
# d = httpserver.http_get('testing.txt')
# print(d)
