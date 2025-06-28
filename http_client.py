import pygame
import sys
import threading
import logging
import time
import requests
from threading import Lock, RLock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from game import (
    get_session_name,
    get_creator_name,
    get_player_name,
    draw_game,
    show_session_menu,
    show_sessions_list,
    init_pygame,
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
        self.server_url = "http://localhost:8885"
        self.selected_cards = []
        self.message = ""
        self.message_timer = 0
        self.in_session = False

        # Add synchronization locks
        self.game_data_lock = RLock()  # Protects game_data updates
        self.command_lock = Lock()  # Prevents concurrent commands
        self.update_lock = Lock()  # Synchronizes update thread

        # Add client-side state tracking
        self.last_update_time = 0
        self.pending_command = False
        self.command_timeout = 10.0  # Timeout for commands
        self.last_successful_update = time.time()

        # Request tracking for preventing duplicate requests
        self.last_command_hash = None
        self.command_count = 0

        # Create a session with optimized connection pooling
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=[
                "HEAD",
                "GET",
                "OPTIONS",
                "POST",
            ],  # Updated parameter name
            backoff_factor=1,
        )

        # Configure adapter with better connection pooling
        adapter = HTTPAdapter(
            pool_connections=2,  # Reduced - you only need 1-2 pools
            pool_maxsize=5,  # Reduced - fewer max connections
            max_retries=retry_strategy,
            pool_block=True,  # Wait for available connection instead of creating new
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set connection timeout and keep-alive
        self.session.timeout = (5, 10)  # (connect_timeout, read_timeout)
        self.session.headers.update(
            {"Connection": "keep-alive", "User-Agent": "CapsaHTTPClient/1.0"}
        )

    def connect_to_server(self):
        try:
            response = self.session.post(
                f"{self.server_url}/api/register",
                json={"client_name": "Player"},
            )

            if response.status_code == 200:
                data = response.json()
                self.client_id = data.get("client_id")
                self.connected = True

                # Start update thread
                update_thread = threading.Thread(
                    target=self.update_game_state, daemon=True
                )
                update_thread.start()

                print(f"Connected to server with client_id: {self.client_id}")
                return True
            else:
                print(f"Failed to connect: {response.status_code}")
                return False

        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def update_game_state(self):
        """Update game state with better error handling"""
        consecutive_errors = 0
        max_errors = 5

        while self.connected:
            try:
                with self.update_lock:
                    if self.in_session and not self.pending_command:
                        response = self.session.get(
                            f"{self.server_url}/api/game_state",
                            params={"client_id": self.client_id},
                            timeout=(3, 5),  # Shorter timeout for frequent requests
                        )

                        if response.status_code == 200:
                            data = response.json()

                            if self.validate_game_data(data):
                                with self.game_data_lock:
                                    current_time = time.time()
                                    if current_time > self.last_update_time:
                                        self.game_data.update(data)
                                        self.last_update_time = current_time
                                        self.last_successful_update = current_time

                                        if (
                                            self.game_data.get(
                                                "current_player_index", -1
                                            )
                                            != self.player_index
                                            and self.selected_cards
                                        ):
                                            self.selected_cards.clear()

                                consecutive_errors = 0
                            else:
                                consecutive_errors += 1
                        else:
                            consecutive_errors += 1

                    # Adaptive polling with longer intervals
                    if self.in_session and self.game_data.get("game_active", False):
                        sleep_time = 2.0  # Increased from 1.0
                    elif self.in_session:
                        sleep_time = 4.0  # Increased from 2.0
                    else:
                        sleep_time = 8.0  # Increased from 5.0

                    time.sleep(sleep_time)

            except requests.exceptions.ConnectionError as e:
                consecutive_errors += 1
                if self.connected:
                    print(f"Connection error #{consecutive_errors}: {e}")
                time.sleep(min(consecutive_errors * 2, 10))

            except Exception as e:
                consecutive_errors += 1
                if self.connected:
                    print(f"Update error #{consecutive_errors}: {e}")

                error_sleep = min(2.0 ** min(consecutive_errors, 5), 10.0)
                time.sleep(error_sleep)

                if consecutive_errors >= max_errors:
                    print("Too many consecutive errors, disconnecting...")
                    self.connected = False
                    break

    def validate_game_data(self, data):
        """Validate game data structure to prevent client crashes"""
        try:
            # Check required fields
            required_fields = [
                "current_player_index",
                "players_names",
                "my_hand",
                "played_cards",
                "players_card_counts",
                "game_active",
            ]

            for field in required_fields:
                if field not in data:
                    return False

            # Validate data types and ranges
            if not isinstance(data["current_player_index"], int):
                return False

            if (
                not isinstance(data["players_names"], list)
                or len(data["players_names"]) != 4
            ):
                return False

            if not isinstance(data["my_hand"], list):
                return False

            if not isinstance(data["played_cards"], list):
                return False

            if (
                not isinstance(data["players_card_counts"], list)
                or len(data["players_card_counts"]) != 4
            ):
                return False

            # Validate card data structure
            for card in data["my_hand"]:
                if (
                    not isinstance(card, dict)
                    or "number" not in card
                    or "suit" not in card
                ):
                    return False

            for card in data["played_cards"]:
                if (
                    not isinstance(card, dict)
                    or "number" not in card
                    or "suit" not in card
                ):
                    return False

            return True

        except Exception as e:
            print(f"Data validation error: {e}")
            return False

    def send_command(self, command):
        """Send command using session with connection pooling"""
        if not self.connected:
            return {"error": "Not connected to server"}

        # Create command hash to prevent duplicates
        command_str = str(sorted(command.items()))
        command_hash = hash(command_str)

        with self.command_lock:
            # Prevent duplicate commands
            if command_hash == self.last_command_hash:
                print("Duplicate command blocked")
                return {"error": "Duplicate command"}

            # Set pending command flag to pause updates
            self.pending_command = True

            try:
                command["client_id"] = self.client_id
                command["command_id"] = self.command_count
                self.command_count += 1

                print(
                    f"Sending command: {command.get('command', 'UNKNOWN')} (ID: {command.get('command_id')})"
                )

                response = self.session.post(
                    f"{self.server_url}/api/command",
                    json=command,
                )

                if response.status_code == 200:
                    data = response.json()
                    self.last_command_hash = command_hash

                    # Force immediate game state update after successful command
                    if "success" in data:
                        self.force_game_state_update()

                    return data
                else:
                    print(f"Command failed: {response.status_code}")
                    return {"error": f"HTTP {response.status_code}"}

            except Exception as e:
                print(f"Send error: {e}")
                return {"error": str(e)}
            finally:
                # Always clear pending flag
                self.pending_command = False

    def force_game_state_update(self):
        """Force update using session"""
        try:
            response = self.session.get(
                f"{self.server_url}/api/game_state",
                params={"client_id": self.client_id},
                timeout=3,
            )

            if response.status_code == 200:
                data = response.json()
                if self.validate_game_data(data):
                    with self.game_data_lock:
                        self.game_data.update(data)
                        self.last_update_time = time.time()
                        self.last_successful_update = time.time()
                        print("Forced game state update successful")
        except Exception as e:
            print(f"Force update error: {e}")

    def is_my_turn(self):
        """Check if it's currently this player's turn"""
        with self.game_data_lock:
            return self.game_data.get(
                "current_player_index", -1
            ) == self.player_index and self.game_data.get("game_active", False)

    def can_play_cards(self):
        """Check if player can currently play cards"""
        return (
            self.is_my_turn()
            and len(self.selected_cards) > 0
            and not self.pending_command
        )

    def can_pass_turn(self):
        """Check if player can pass their turn"""
        return (
            self.is_my_turn()
            and not self.pending_command
            and len(self.game_data.get("played_cards", [])) > 0
        )

    def handle_session_menu(self):
        """Update session menu methods to use session"""
        while True:
            choice = show_session_menu()

            if choice == 1:
                session_name = get_session_name()
                creator_name = get_creator_name()

                response = self.session.post(
                    f"{self.server_url}/api/create_session",
                    json={
                        "client_id": self.client_id,
                        "session_name": session_name,
                        "creator_name": creator_name,
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    if "success" in data:
                        # Get session info after creation
                        info_response = self.session.get(
                            f"{self.server_url}/api/session_info",
                            params={"client_id": self.client_id},
                        )
                        if info_response.status_code == 200:
                            info = info_response.json()
                            with self.game_data_lock:
                                self.session_id = info.get("session_id")
                                self.session_name = info.get("session_name")
                                self.player_index = info.get("player_index")
                                self.player_name = info.get("player_name")
                                self.in_session = True

                            print(
                                f"Successfully created session '{self.session_name}' as {self.player_name}"
                            )
                            print("Opening game UI...")
                            return
                    else:
                        print("Failed to create session")
                else:
                    print("Failed to create session")

            elif choice == 2:
                response = self.session.get(
                    f"{self.server_url}/api/sessions",
                    params={"client_id": self.client_id},
                )

                if response.status_code == 200:
                    data = response.json()
                    if "sessions" in data:
                        session_id = show_sessions_list(data["sessions"])

                        if session_id:
                            player_name = get_player_name()

                            join_response = self.session.post(
                                f"{self.server_url}/api/join_session",
                                json={
                                    "client_id": self.client_id,
                                    "session_id": session_id,
                                    "player_name": player_name,
                                },
                            )

                            if join_response.status_code == 200:
                                join_data = join_response.json()
                                if "success" in join_data:
                                    info_response = self.session.get(
                                        f"{self.server_url}/api/session_info",
                                        params={"client_id": self.client_id},
                                    )
                                    if info_response.status_code == 200:
                                        info = info_response.json()
                                        with self.game_data_lock:
                                            self.session_id = info.get("session_id")
                                            self.session_name = info.get("session_name")
                                            self.player_index = info.get("player_index")
                                            self.player_name = info.get("player_name")
                                            self.in_session = True

                                        print(
                                            f"Successfully joined session '{self.session_name}' as {self.player_name}"
                                        )
                                        print("Opening game UI...")
                                        return
                                elif "error" in join_data:
                                    print(
                                        f"Failed to join session: {join_data['error']}"
                                    )
                                else:
                                    print("Failed to join session")
                            else:
                                print("Failed to join session")
                    else:
                        print("Failed to get session list")
                else:
                    print("Failed to get session list")

            elif choice == 3:
                print("Goodbye!")
                sys.exit(0)

    def show_message(self, message, duration=180):
        self.message = message
        self.message_timer = duration

    def __del__(self):
        """Clean up session on destruction"""
        if hasattr(self, "session"):
            self.session.close()


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
                # Use game_data_lock when accessing game data
                with client.game_data_lock:
                    card_rects, button_rects = draw_game(screen, client, WIDTH, HEIGHT)

                # Handle card selection
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

                # Handle button clicks with validation
                for button_type, rect in button_rects:
                    if rect.collidepoint(event.pos):
                        print(f"Button clicked: {button_type}")

                        if button_type == "PLAY" and client.can_play_cards():
                            card_numbers = [
                                card["number"] for card in client.selected_cards
                            ]
                            print(f"Playing cards: {card_numbers}")
                            response = client.send_command(
                                {"command": "PLAY_CARDS", "cards": card_numbers}
                            )
                            if response and "error" in response:
                                client.show_message(response["error"])
                            elif response and "success" in response:
                                client.show_message("Cards played successfully!")
                            client.selected_cards.clear()

                        elif button_type == "PASS" and client.can_pass_turn():
                            print("Passing turn")
                            response = client.send_command({"command": "PASS_TURN"})
                            if response and "error" in response:
                                client.show_message(response["error"])
                            elif response and "success" in response:
                                client.show_message("Turn passed!")
                            client.selected_cards.clear()

                        elif button_type == "START" and not client.pending_command:
                            print("Starting game")
                            response = client.send_command({"command": "START_GAME"})
                            if response and "error" in response:
                                client.show_message(response["error"])
                            elif response and "success" in response:
                                client.show_message("Game started!")
                        break

        # Draw game with proper synchronization
        with client.game_data_lock:
            draw_game(screen, client, WIDTH, HEIGHT)

        pygame.display.flip()
        clock.tick(FPS)

    client.connected = False
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
