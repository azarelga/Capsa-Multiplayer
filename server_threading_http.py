from socket import *
import socket
import time
import sys
import logging
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from http_server import HttpServer
from collections import defaultdict

httpserver = HttpServer()

# Global lock for HTTP request synchronization
http_request_lock = threading.RLock()  # Use RLock to allow nested locking

# Add this at module level
recent_clients = {}
client_request_counts = defaultdict(int)


# Function to process each client connection
def ProcessTheClient(connection, address):
    client_id = f"{address[0]}:{address[1]}:{int(time.time() * 1000) % 10000}"

    # Only log new unique clients, not every connection
    client_ip = address[0]
    current_time = time.time()

    # Track requests per IP instead of per connection
    client_request_counts[client_ip] += 1

    # Only log significant events
    if (
        client_ip not in recent_clients
        or (current_time - recent_clients[client_ip]) > 30
    ):
        print(
            f"HTTP client from {client_ip} (connection #{client_request_counts[client_ip]})"
        )
        recent_clients[client_ip] = current_time

    rcv = b""

    try:
        # Step 1: Read until we get all headers (\r\n\r\n)
        while b"\r\n\r\n" not in rcv:
            data = connection.recv(8192)
            if not data:
                break
            rcv += data

        if not rcv:
            connection.close()
            return

        # Step 2: Split headers and body-start
        header_part, _, body_start = rcv.partition(b"\r\n\r\n")
        headers_text = header_part.decode(errors="replace")
        headers = headers_text.split("\r\n")

        # Step 3: Find Content-Length
        content_length = 0
        for h in headers:
            if h.lower().startswith("content-length:"):
                content_length = int(h.split(":", 1)[1].strip())
                break

        # Step 4: Read the rest of the body
        body = body_start
        while len(body) < content_length:
            chunk = connection.recv(8192)
            if not chunk:
                break
            body += chunk

        # Step 5: Reconstruct full HTTP request for processing
        full_request = headers_text + "\r\n\r\n" + body.decode(errors="replace")

        # Step 6: Determine if this request needs synchronization
        request_line = headers_text.split("\n")[0] if headers_text else ""
        needs_sync = should_synchronize_request(request_line)

        # Less verbose logging - only log non-routine requests
        if headers_text.split()[1] not in ["/api/game_state", "/api/ping"]:
            print(
                f"Request from {client_ip}: {headers_text.split()[0]} {headers_text.split()[1]} [Sync: {needs_sync}]"
            )

        # Step 7: Process with or without synchronization
        if needs_sync:
            with http_request_lock:
                hasil = httpserver.proses(full_request)
        else:
            hasil = httpserver.proses(full_request)

        connection.sendall(hasil)

    except Exception as e:
        print(f"[!] Error processing client from {client_ip}: {e}")
        try:
            if "needs_sync" in locals() and needs_sync:
                with http_request_lock:
                    error_response = httpserver.response(
                        500, "Internal Server Error", "Server error occurred"
                    )
            else:
                error_response = httpserver.response(
                    500, "Internal Server Error", "Server error occurred"
                )
            connection.sendall(error_response)
        except:
            pass

    finally:
        # Don't log every connection close
        connection.close()


def should_synchronize_request(request_line):
    """Determine if a request needs synchronization based on the request path"""
    try:
        parts = request_line.split()
        if len(parts) < 2:
            return False

        method = parts[0].upper()
        path = parts[1]

        # Synchronize game-related API endpoints
        game_endpoints = [
            "/api/game",
            "/api/command",
            "/api/create_session",
            "/api/join_session",
            "/api/game_state",
            "/api/sessions",
        ]

        # Always sync POST requests to API endpoints
        if method == "POST" and path.startswith("/api/"):
            return True

        # Sync specific GET endpoints that modify or read game state
        if method == "GET":
            for endpoint in game_endpoints:
                if path.startswith(endpoint):
                    return True

        return False

    except:
        # If we can't parse the request, err on the side of caution
        return True


def Server():
    the_clients = []
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        my_socket.bind(("0.0.0.0", 8885))
        my_socket.listen(20)

        print("=" * 60)
        print("CAPSA MULTIPLAYER HTTP GAME SERVER STARTED")
        print("=" * 60)
        print(f"HTTP Server listening on port 8885")
        print(f"Access game at: http://localhost:8885")
        print(f"API endpoints available at: http://localhost:8885/api/")
        print(f"Supports concurrent HTTP requests")
        print("=" * 60)

        with ThreadPoolExecutor(20) as executor:
            client_counter = 0

            while True:
                try:
                    connection, client_address = my_socket.accept()
                    client_counter += 1

                    print(
                        f"HTTP Client #{client_counter} connected from {client_address}"
                    )

                    # Submit client processing to thread pool
                    p = executor.submit(ProcessTheClient, connection, client_address)
                    the_clients.append(p)

                    # Clean up completed threads and show active count
                    active_clients = [i for i in the_clients if i.running() == True]
                    the_clients = active_clients  # Remove completed threads from list

                    # Status information
                    registered_clients = len(httpserver.game_server.clients)
                    active_sessions = len(httpserver.game_server.sessions)

                    print(
                        f"Active threads: {len(active_clients)} | "
                        f"Registered clients: {registered_clients} | "
                        f"Active sessions: {active_sessions}"
                    )

                except KeyboardInterrupt:
                    print("\nShutting down HTTP server...")
                    break
                except Exception as e:
                    print(f"Error accepting connection: {e}")

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        print("HTTP Server shutting down...")
        httpserver.running = False
        try:
            my_socket.close()
        except:
            pass


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    try:
        Server()
    except KeyboardInterrupt:
        print("\nHTTP Server stopped by user")
    except Exception as e:
        print(f"HTTP Server error: {e}")


if __name__ == "__main__":
    main()
