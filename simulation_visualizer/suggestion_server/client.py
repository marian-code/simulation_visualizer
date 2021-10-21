import logging
import os
import pickle
import socket
import struct
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    Picklable = TypeVar("Picklable")

DEFAULT_SOCK_ADDR = "/tmp/socket_suggestion_server_plot.s"
CONNECTION_TIMEOUT = 0.001

log = logging.getLogger(__name__)


class SocketClient:
    """Client side implementation of basic sequential socket server."""

    def __init__(self, address: str):

        log.debug("creating socket")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        log.debug("attempting to connect to server")

        self.sock.settimeout(CONNECTION_TIMEOUT)
        try:
            self.sock.connect(address)
        except FileNotFoundError:
            raise ConnectionRefusedError("could not connect to suggestion server")
        except socket.timeout:
            raise TimeoutError("could not connect to socket in specified time")
        else:
            log.debug("succesfully connected to server")
        finally:
            self.sock.settimeout(None)

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
        """Read message from server.

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


def connect_to_suggestion_server(
    *, log_level: int, unique_socket_address: Path
) -> "SocketClient":
    """Establis connection to server providing autocomplete suggestions.

    Parametrers
    -----------
    log_level: int
        logging level to setup server logger
    unique_socket_address: Path
        server <-> client communication socket address, location must be
        writable

    Returns
    -------
    SocketClient
        client side connected to server

    Raises
    ------
    TimeoutError
        if connection attempt has timed out three times
    """
    started = False
    timeout_counter = 0

    log.debug(f"logging for server is set to: {log_level}")

    while True:
        try:
            cl = SocketClient(str(unique_socket_address))
        except ConnectionRefusedError:
            log.warn("connection refused")
            if not started:
                log.warn("server not running, starting...")
                start_server(log_level, unique_socket_address)
                started = True
        except TimeoutError:
            log.warn("connection to socket server timed out")
            if timeout_counter > 3:
                raise TimeoutError(
                    "three attempts to connect to suggestion server have timed out"
                )
            else:
                timeout_counter += 1
        else:
            return cl


def start_server(log_level: int, unique_socket_address: Path):
    """Start socket server.

    Parametrers
    -----------
    log_level: int
        logging level to setup server logger
    unique_socket_address: Path
        server <-> client communication socket address, location must be
        writable
    """
    # delete socket file
    log.debug("removing socket file")
    try:
        os.unlink(unique_socket_address)
    except FileNotFoundError:
        pass

    # start server
    log.debug("spawnig server process")
    subprocess.Popen(
        [get_python(), "server.py", str(unique_socket_address), str(log_level)],
        cwd=os.path.dirname(__file__),
    )

    # with until server creates socket file
    log.debug("waiting until server creates socket file")
    while not unique_socket_address.exists():
        time.sleep(CONNECTION_TIMEOUT)


def get_python() -> str:
    """Get path of python executable.

    Returns
    -------
    str
        path pointing to python binary
    """
    p = str(Path(os.__file__).parents[2] / "bin" / "python")
    log.debug(f"got python path: {p}")
    return p
