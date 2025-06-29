from socket import *
import logging
import threading
import socketserver
from custom_http import HttpServer

# A single, shared instance of the HttpServer to maintain game state
httpserver = HttpServer()


class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        try:
            data = self.request.recv(4096).strip()
            if not data:
                return

            # logging.info(f"---REQUEST FROM {self.client_address}---")
            # logging.info(data.decode())
            # logging.info("---------------------")

            # Process the request using the shared httpserver instance
            response = httpserver.proses(data.decode())

            if data.startswith(b"POST"):    
                logging.info(f"---RESPONSE TO {self.client_address}---")
                logging.info(response.decode())
                logging.info("---------------------")

            self.request.sendall(response)
        except Exception as e:
            logging.error(f"Error handling request from {self.client_address}: {e}")


def main():
    HOST, PORT = "0.0.0.0", 8886

    logging.basicConfig(level=logging.INFO)
    logging.info(f"Server starting on {HOST}:{PORT}")

    # Create the server, binding to localhost on port 8886
    with socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
