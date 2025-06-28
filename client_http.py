import pygame
import requests
import json
import time
from game import (
    show_session_menu,
    get_session_name,
    get_creator_name,
    show_sessions_list,
    get_player_name,
    init_pygame,
    draw_game,
    GameState,
)


class CapsaClient:
    def __init__(self, server_address):
        self.server_address = server_address
        self.session_id = None
        self.session_name = None
        self.creator_name = None
        self.creator_index = -1
        self.player_id = None
        self.session_data = {}
        self.player_name = None
        self.player_index = -1
        self.game_data = self._get_default_game_data()
        self.connected = False
        self.message = ""
        self.message_timer = 0
        self.selected_cards = []

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
        try:
            response = requests.get(f"{self.server_address}/sessions")
            if response.status_code == 200:
                return response.json()
            return []
        except requests.exceptions.ConnectionError:
            return None

    def create_session(self, session_name, creator_name):
        try:
            response = requests.post(
                f"{self.server_address}/sessions",
                json={"session_name": session_name, "creator_name": creator_name},
            )
            if response.status_code == 201:
                session_data = response.json()
                self.session_id = session_data["session_id"]
                self.session_name = session_name
                self.player_name = creator_name
                self.connected = True
                return True
            return False
        except requests.exceptions.ConnectionError:
            return False

    def join_session(self, session_id, player_name):
        try:
            response = requests.post(
                f"{self.server_address}/sessions/{session_id}/join",
                json={"player_name": player_name},
            )
            if response.status_code == 200:
                session_data = response.json()
                self.session_id = session_id
                self.player_name = player_name
                self.session_name = session_data.get("session_name")
                self.connected = True
                return True
            return False
        except requests.exceptions.ConnectionError:
            return False

    def start_game(self):
        try:
            response = requests.post(
                f"{self.server_address}/sessions/{self.session_id}/start"
            )
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    def get_game_state(self):
        if not self.session_id or not self.player_name:
            return
        try:
            response = requests.get(
                f"{self.server_address}/sessions/{self.session_id}?player_name={self.player_name}"
            )
            if response.status_code == 200:
                new_game_data = self._get_default_game_data()
                new_game_data.update(response.json())
                self.game_data = new_game_data
                self.player_index = self.game_data.get("my_player_index", -1)
            else:
                self.connected = False  # Assume disconnected if we can't get state
                self.game_data = self._get_default_game_data()
        except requests.exceptions.ConnectionError:
            self.connected = False
            self.game_data = self._get_default_game_data()

    def play_cards(self, card_indices):
        try:
            response = requests.post(
                f"{self.server_address}/sessions/{self.session_id}/play",
                json={"player_name": self.player_name, "cards": card_indices},
            )
            if response.status_code != 200:
                self.show_message(response.json().get("error", "Invalid move"), 2)
            else:
                self.selected_cards = []  # Clear selection after successful play
        except requests.exceptions.ConnectionError:
            self.show_message("Connection error", 2)

    def pass_turn(self):
        try:
            response = requests.post(
                f"{self.server_address}/sessions/{self.session_id}/pass",
                json={"player_name": self.player_name},
            )
            if response.status_code != 200:
                self.show_message(response.json().get("error", "Cannot pass"), 2)
        except requests.exceptions.ConnectionError:
            self.show_message("Connection error", 2)

    def show_message(self, text, duration):
        self.message = text
        self.message_timer = duration * 60  # duration in seconds, 60 FPS


def main():
    server_address = "http://127.0.0.1:8886"
    client = CapsaClient(server_address)

    while not client.connected:
        choice = show_session_menu()

        if choice == 1:
            session_name = get_session_name()
            creator_name = get_creator_name()
            if client.create_session(session_name, creator_name):
                print(f"Session '{session_name}' created. Waiting for other players...")
                break
            else:
                print("Could not create session. Is the server running?")
                return
        elif choice == 2:
            sessions = client.get_sessions()
            if sessions is None:
                print("Could not connect to the server.")
                return
            if not sessions:
                print("No sessions available.")
                continue

            # show_sessions_list now returns the session_id directly
            session_id = show_sessions_list(sessions)
            if session_id:
                player_name = get_player_name()
                if not client.join_session(session_id, player_name):
                    print("Failed to join session.")
                else:
                    print(
                        f"Joined session '{client.session_name}'. Waiting for game to start..."
                    )
                    break

        elif choice == 3:
            return

    # Pygame loop
    screen, clock, WIDTH, HEIGHT, FPS = init_pygame()
    running = True
    card_rects, button_rects = [], []
    while running:
        client.get_game_state()

        if not client.connected:
            print("Lost connection to server.")
            running = False
            continue

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Card selection logic
                if client.game_data.get("my_hand"):
                    for rect, card_data in card_rects:
                        if rect.collidepoint(event.pos):
                            card_number = card_data["number"]
                            # Find the index of the card in the original hand
                            for i, c in enumerate(client.game_data["my_hand"]):
                                if c["number"] == card_number:
                                    if i in client.selected_cards:
                                        client.selected_cards.remove(i)
                                    else:
                                        client.selected_cards.append(i)
                                    client.selected_cards.sort()
                                    break

                # Button click logic
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

        card_rects, button_rects = draw_game(screen, client, WIDTH, HEIGHT)
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
