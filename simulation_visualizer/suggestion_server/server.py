"""bash autocompletion suggestion server.

Server implementation is usefull because some actions require remote SSH or SQL
connection which takes long to establish, so this duty is passed to server
which establishes connections as needed and holds them running in the
background so they do not have to be opened anew. When suggestions
are finished server quietly exits after timeout.
"""

import atexit
import logging
import pickle
import socket
import struct
import sys
from os import remove
from typing import TYPE_CHECKING, TypeVar

from simulation_visualizer.path_completition import Completion

SERVER_WAITING_CLIENTS: int = 5
SOCK_SERVER_TIMEOUT: int = 30

if TYPE_CHECKING:
    Picklable = TypeVar("Picklable")

log = logging.getLogger("simulation_visualizer.suggestion_server")
logging.getLogger("paramiko").setLevel(logging.WARNING)
logging.getLogger("ssh_utilities").setLevel(logging.WARNING)


class SocketServer:
    """Server side implementation of basic seqntuial socket server."""

    def __init__(self, address) -> None:

        # AF_UNIX are unix file-like sockets that bind to a file, this is fast
        # enough for our purposes
        log.debug("creating socket")
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        log.debug(f"binding addres to: {address}")
        self.s.bind(address)

        log.debug(f"max requests: {SERVER_WAITING_CLIENTS}")
        self.s.listen(SERVER_WAITING_CLIENTS)

        log.debug(f"set to accept connections")
        self.sock, _ = self.s.accept()

        log.debug("started suggestion server")

    def write(self, data: "Picklable"):
        """Send data to client.

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
        """Read from message from client.

        Returns
        -------
        Picklable
            any picklable data type send by client
        """
        # first receive number of bytes that will follow, unpack returns a
        # one-tuple
        log.debug("receiving data length")
        r = self.sock.recv(4)

        if len(r) == 0:
            self.s.settimeout(SOCK_SERVER_TIMEOUT)
            self.sock, _ = self.s.accept()
            log.warning("read zero length byte, client has disconnected")
            return self.read()
        else:
            length = struct.unpack("i", r)[0]
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
        """Close server side socket connection."""
        log.debug("exiting")
        self.sock.close()


def server(address: str, log_level: str):
    """Main suggestion server loop, answers to client requests.

    Parameters
    ----------
    address : Union[Path, str]
        server socket address (filename), we are using posix sockets
    log_level: str
        logging level
    """
    function: str
    kwargs: dict

    #set_log_handles(log_level, log_file="server.log")
    # ! this is error prone when some changes are implemented
    log_id = address.replace("/tmp/user-", "").replace("-suggestion_server", "")

    logging.basicConfig(
        filename=f"../logs/suggestion_server-{log_id}.log",
        level=int(log_level), filemode="w",
        format="[%(asctime)s] %(levelname)-7s ""%(name)-45s %(message)s"
    )

    server = SocketServer(address)
    # remove socket file when exiting
    atexit.register(remove, address)
    cp = Completion()

    log.debug("entering loop")

    while True:

        # read client request
        try:
            function, kwargs = server.read()
        except socket.timeout:
            server.close()
            return
        else:
            # get appropriate method
            f = getattr(cp, function, None)
            log.debug(f"found function: {f}")

            # get method output, and send it back to client
            log.debug("sending answer to client")
            server.write(f(**kwargs))


if __name__ == "__main__":
    # first argument is script name, second socket path and last logger level
    server(*sys.argv[1:])
