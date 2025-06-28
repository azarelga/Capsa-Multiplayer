import pygame
import sys
import threading
import logging
import time
import requests

from game import (
    get_session_name, 
    get_creator_name, 
    get_player_name,
    draw_game,
    show_session_menu,
    show_sessions_list,
    init_pygame
)

class CapsaHTTPClient:
    def __init__(self):
        self.connected = False
        self.session_id = None
        self.session_name = ""
        self.player_index = -1
        self.player_name = ""
        self.client_id = None
        self.game_data = {
            "current_player_index": 0,
            "current_player_name": "",
            "players_names": ["", "", "", ""],
            "my_hand": [],
            "played_cards": [],
            "players_card_counts": [0, 0, 0, 0],
            "game_active": False,
            "winner": None,
            "players_passed": [],
        }
        self.server_url = "http://localhost:8080"
        self.selected_cards = []
        self.message = ""
        self.message_timer = 0
        self.in_session = False

    def connect_to_server(self):
        try:
            response = requests.post(
                f"{self.server_url}/api/register", json={"client_name": "Player"}, timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                self.client_id = data.get("client_id")
                self.connected = True

                update_thread = threading.Thread(
                    target=self.update_game_state, daemon=True
                )
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
                    response = requests.get(
                        f"{self.server_url}/api/game_state?client_id={self.client_id}",
                        timeout=5,
                    )
                    time.sleep(1)  # 500ms during game

                    if response.status_code == 200:
                        data = response.json()
                        # Update game data directly
                        if "current_player_index" in data:
                            self.game_data.update(data)

                time.sleep(5)  # Changed from 0.001 to 0.5 seconds (500ms)

            except Exception as e:
                if self.connected:
                    logging.warning(f"Update error: {e}")
                time.sleep(1.0)  # Changed from 0.05 to 1.0 seconds on error

    def send_command(self, command):
        if not self.connected:
            return None

        try:
            command["client_id"] = self.client_id
            response = requests.post(
                f"{self.server_url}/api/command", json=command, timeout=10
            )

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

                response = requests.post(
                    f"{self.server_url}/api/create_session",
                    json={
                        "client_id": self.client_id,
                        "session_name": session_name,
                        "creator_name": creator_name,
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if "success" in data:
                        # Get session info after creation
                        info_response = requests.get(
                            f"{self.server_url}/api/session_info?client_id={self.client_id}",
                            timeout=5
                        )
                        if info_response.status_code == 200:
                            info = info_response.json()
                            self.session_id = info.get("session_id")
                            self.session_name = info.get("session_name")
                            self.player_index = info.get("player_index")
                            self.player_name = info.get("player_name")
                            self.in_session = True

                            print(
                                f"Berhasil membuat session '{self.session_name}' sebagai {self.player_name}"
                            )
                            print("Membuka game UI...")
                            return
                    else:
                        print("Gagal membuat session")
                else:
                    print("Gagal membuat session")

            elif choice == 2:
                response = requests.get(
                    f"{self.server_url}/api/sessions?client_id={self.client_id}",
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    if "sessions" in data:
                        session_id = show_sessions_list(data["sessions"])

                        if session_id:
                            player_name = get_player_name()

                            join_response = requests.post(
                                f"{self.server_url}/api/join_session",
                                json={
                                    "client_id": self.client_id,
                                    "session_id": session_id,
                                    "player_name": player_name,
                                },
                                timeout=10
                            )

                            if join_response.status_code == 200:
                                join_data = join_response.json()
                                if "success" in join_data:
                                    # Get session info after joining
                                    info_response = requests.get(
                                        f"{self.server_url}/api/session_info?client_id={self.client_id}",
                                        timeout=5
                                    )
                                    if info_response.status_code == 200:
                                        info = info_response.json()
                                        self.session_id = info.get("session_id")
                                        self.session_name = info.get("session_name")
                                        self.player_index = info.get("player_index")
                                        self.player_name = info.get("player_name")
                                        self.in_session = True

                                        print(
                                            f"Berhasil join session '{self.session_name}' sebagai {self.player_name}"
                                        )
                                        print("Membuka game UI...")
                                        return
                                elif "error" in join_data:
                                    print(f"Gagal join session: {join_data['error']}")
                                else:
                                    print("Gagal join session")
                            else:
                                print("Gagal join session")
                    else:
                        print("Gagal mendapatkan daftar session")
                else:
                    print("Gagal mendapatkan daftar session")

            elif choice == 3:
                print("Goodbye!")
                sys.exit(0)

    def show_message(self, message, duration=180):
        self.message = message
        self.message_timer = duration


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
                        print(
                            f"Card clicked: {card['pp_value']} of suit {card['suit']}"
                        )
                        break

                for button_type, rect in button_rects:
                    if rect.collidepoint(event.pos):
                        print(f"Button clicked: {button_type}")
                        if button_type == "PLAY" and client.selected_cards:
                            card_numbers = [
                                card["number"] for card in client.selected_cards
                            ]
                            print(f"Playing cards: {card_numbers}")
                            response = client.send_command(
                                {"command": "PLAY_CARDS", "cards": card_numbers}
                            )
                            if response and "error" in response:
                                client.show_message(response["error"])
                            elif response and "winner" in response:
                                client.show_message(f"{response['winner']} wins!")
                            client.selected_cards.clear()
                        elif button_type == "PASS":
                            print("Passing turn")
                            response = client.send_command({"command": "PASS_TURN"})
                            if response and "error" in response:
                                client.show_message(response["error"])
                            client.selected_cards.clear()
                        elif button_type == "START":
                            print("Starting game")
                            response = client.send_command({"command": "START_GAME"})
                            if response and "error" in response:
                                client.show_message(response["error"])
                        break

        draw_game(screen, client, WIDTH, HEIGHT)
        pygame.display.flip()
        clock.tick(FPS)

    client.connected = False
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

