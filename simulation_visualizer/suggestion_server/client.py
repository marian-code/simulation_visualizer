import logging
import os
import pickle
import socket
import struct
import subprocess
import time
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    Picklable = TypeVar("Picklable")

DEFAULT_SOCK_ADDR = "/tmp/socket_suggestion_server_plot.s"

log = logging.getLogger(__name__)


class SocketClient:
    """Client side implementation of basic sequential socket server."""

    def __init__(self, address: str):

        log.debug("creating socket")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        log.debug("attempting to connect to server")
        try:
            self.sock.connect(address)
        except FileNotFoundError:
            raise ConnectionRefusedError("could not connect to "
                                         "suggestion server")
        else:
            log.debug("succesfully connected to server")

    def write(self, data: "Picklable"):
        """Send data to server.

        Parameters
        ----------
        data : Picklable
            any python data structure that is picklable
        """
        log.debug(f"sending data from sercer to client: {data}")

        # first pickle data and get bytes length
        data_bytes = pickle.dumps(data)
        length = struct.pack("i", len(data_bytes))

        # send number of bytes that the other side is to receive
        self.sock.send(length)

        # send the actual message
        self.sock.send(data_bytes)

    def read(self) -> "Picklable":
        """Read from message from server.

        Returns
        -------
        Picklable
            any picklable data type send by server
        """
        # first receive number of bytes that will follow, unpack returns a
        # one-tuple
        log.debug("receiving data length")
        length = struct.unpack("i", self.sock.recv(4))[0]

        log.debug(f"data length is: {length}")
        log.debug("receiving actual data")

        # now load actual data
        output = b""
        while True:
            output += self.sock.recv(4096)
            if len(output) >= length:
                break

        data = pickle.loads(output)

        log.debug(f"got data: {data}")

        return data

    def close(self):
        """Close client side socket connection."""
        log.debug("exiting")
        self.sock.close()


def connect_to_suggestion_server(*, log_level: int, unique_socket_address: str
                                 ) -> "SocketClient":
    """Establis connection to server providing autocomplete suggestions.

    Parametrers
    -----------
    log_level: int
        logging level to setup server logger
    unique_socket_address: str
        server <-> client communication socket address, location must be
        writable

    Returns
    -------
    SocketClient
        client side connected to server
    """
    started = False

    log.debug(f"logging for server is set to: {log_level}")

    while True:
        try:
            cl = SocketClient(unique_socket_address)
        except ConnectionRefusedError:
            log.warn("connection refused")
            if not started:
                log.warn("server not running, starting...")

                # delete socket file
                log.debug("removing socket file")
                if os.path.exists(unique_socket_address):
                    os.remove(unique_socket_address)

                # start server
                log.debug("spawnig server process")
                subprocess.Popen(["python", "server.py",
                                  unique_socket_address, str(log_level)],
                                 cwd=os.path.dirname(__file__))

                # with until server creates socket file
                log.debug("waiting until server creates socket file")
                while not os.path.exists(unique_socket_address):
                    time.sleep(0.001)

                started = True
        else:
            return cl
