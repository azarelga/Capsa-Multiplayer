from socket import *
import socket
import time
import sys
import logging
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http_game import CapsaGameServer

game_server = CapsaGameServer()


def ProcessTheClient(connection, address):
    client_id = f"{address[0]}:{address[1]}:{int(time.time() * 1000) % 10000}"

    print(f"New client connected: {client_id} from {address}")

    game_server.add_client(client_id, connection)

    rcv = ""
    try:
        while True:
            try:
                connection.settimeout(30.0)
                data = connection.recv(1024)

                if data:
                    d = data.decode()
                    rcv = rcv + d

                    while '\n' in rcv:
                        line, rcv = rcv.split('\n', 1)
                        if line.strip():
                            try:
                                command = json.loads(line.strip())
                                print(f"Command from {client_id}: {command}")
                                game_server.handle_command(client_id, command)
                            except json.JSONDecodeError as e:
                                logging.warning(f"Invalid JSON from {client_id}: {line} | Error: {e}")
                else:
                    print(f"Client {client_id} disconnected (no data)")
                    break

            except socket.timeout:
                try:
                    ping_msg = json.dumps({'command': 'PING'}) + '\n'
                    connection.send(ping_msg.encode())
                    print(f"Ping sent to {client_id}")
                except:
                    print(f"Client {client_id} ping failed - disconnecting")
                    break

            except OSError as e:
                print(f"OSError from {client_id}: {e}")
                break
            except Exception as e:
                print(f"Unexpected error from {client_id}: {e}")
                break

    except Exception as e:
        logging.warning(f"Error handling client {client_id}: {e}")
    finally:
        print(f"Cleaning up client {client_id}")
        game_server.remove_client(client_id)
        try:
            connection.close()
        except:
            pass


def Server():
    active_clients = []
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        my_socket.bind(('0.0.0.0', 55556))
        my_socket.listen(20)

        print("=" * 50)
        print("CAPSA MULTIPLAYER GAME SERVER STARTED")
        print("=" * 50)
        print(f"Listening on port 55556")
        print(f"Connect clients to: localhost:55556")
        print(f"Supports 1-4 players (AI fills empty slots)")
        print("=" * 50)

        with ThreadPoolExecutor(max_workers=10) as executor:
            client_counter = 0

            while True:
                try:
                    connection, client_address = my_socket.accept()
                    client_counter += 1

                    print(f"Client #{client_counter} connected from {client_address}")

                    future = executor.submit(ProcessTheClient, connection, client_address)
                    active_clients.append(future)

                    active_clients = [f for f in active_clients if f.running()]

                    active_count = len(active_clients)
                    human_players = len(game_server.clients)
                    ai_players = 4 - human_players if human_players > 0 else 0

                    print(f"Active connections: {active_count} | Human players: {human_players} | AI players: {ai_players}")

                except Exception as e:
                    logging.error(f"Error accepting connection: {e}")

    except Exception as e:
        logging.error(f"Server error: {e}")
    finally:
        print("Server shutting down...")
        game_server.running = False
        my_socket.close()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        Server()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        print(f"Server error: {e}")


if __name__ == "__main__":
    main()