from socket import *
import logging
import threading
import socketserver
from .http_protocol import HttpServer

# A single, shared instance of the HttpServer to maintain game state
httpserver = HttpServer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            if data.startswith(b"POST"):    
                logger.info(f"---REQUEST FROM {self.client_address}---")
                logger.info(data.decode())
                logger.info("---------------------")

            # Process the request using the shared httpserver instance
            response = httpserver.proses(data.decode())

            if data.startswith(b"POST"):    
                logger.info(f"---RESPONSE TO {self.client_address}---")
                logger.info(response.decode())
                logger.info("---------------------")

            self.request.sendall(response)
        except Exception as e:
            logging.error(f"Error handling request from {self.client_address}: {e}")


def main():
    HOST, PORT = "0.0.0.0", 8886

    logging.basicConfig(level=logging.INFO)
    logger.info(f"Server starting on {HOST}:{PORT}")

    # Create the server, binding to localhost on port 8886
    with socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
