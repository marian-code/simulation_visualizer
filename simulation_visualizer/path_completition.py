import logging
from socket import gethostname
from typing import TYPE_CHECKING, Dict, List, Union

from ssh_utilities import Connection

from simulation_visualizer.suggestion_server.client import \
    connect_to_suggestion_server

if TYPE_CHECKING:
    from pathlib import Path

    from ssh_utilities import LocalConnection, SSHConnection
    _CONN = Union[LocalConnection, SSHConnection]


log = logging.getLogger(__name__)


class Completion:
    """Class providing completions that are dependent on remote access."""

    def __init__(self):

        log.debug("initalized completion class")

        self._c = None

    def c(self, host: str) -> "_CONN":
        """Holds ssh connection object.

        Parameters
        ----------
        host : str
            server name

        Returns
        -------
        Connection
            initialized SSHConnection object
        """
        local = True if host == gethostname().lower() else False
        log.debug(f"local: {local}, hostname: {gethostname()}")
        # open connection to host
        if not self._c:
            log.info(f"connecting to server {host}")
            self._c = Connection(host.lower(), local=local, quiet=True)
        # if host changed establish new connection
        elif self._c.server_name != host.upper():
            log.info(f"changing connection from server: {self._c.server_name} "
                     f"to {host.upper()}")
            self._c.close()
            self._c = Connection(host.lower(), local=local, quiet=True)

        return self._c

    def get_dirs(self, host: str, input_path: str) -> List[str]:
        """Suggest dirs on remote server to submit to.

        Parameters
        ----------
        host: str
            host name
        input_path : str
            partialy completed path
        kwargs: dict
            dictionary of autocompleter arguments

        Returns
        -------
        List[str]
            sequence of possible directories based on alredy parsed input
        """
        input_path = input_path.strip()

        if not input_path:
            return ["/home/"]

        path = self.c(host).pathlib.Path(input_path)
        log.debug(f"got base path: {path}")

        if path.is_file():
            log.debug(f"path is file, returning ...")
            return [str(path)]

        while True:

            log.debug(f"checking path: {path}, is dir: {path.is_dir()}")
            if path.is_dir():
                dirs_files = [d for d in self.c(host).pathlib.Path(path).glob("*")]
                log.debug(f"got dir contents: {dirs_files}")
                break
            else:
                parent = path.parent
                if path == parent:
                    log.warning("got to the bottom of directory tree")
                    dirs_files = [d for d in parent.glob("*")]
                    break
                else:
                    path = parent
                    log.debug(f"got path parent: {path}")

        log.debug("filtering dirs and files")
        paths = []
        for d in dirs_files:
            if d.is_dir():
                paths.append(f"{d}/")
            else:
                paths.append(str(d))

        log.debug("sorting and returning")
        return sorted(paths)


class Suggest:
    """Callable class that mediates suggestions.

    Decides between server or serverless bakend.

    Parameters
    ----------
    function_name: str
        name of the Comlpetion class method that will be used for suggestions
    """

    def __init__(self, function_name: str):
        self.function = function_name

    def __call__(self, host: str, filename: str, unique_socket_address: "Path"
                 ) -> List[str]:
        """Proxy for autocompleter methods.

        Parameters
        ----------
        host : str
            name of the host server
        filename : str
            parsed part of the path being currently completed
        unique_socket_address: str
            server <-> client communication socket address, location must be
            writable. Each user must have his own server

        Returns
        -------
        List[str]
            [description]
        """
        kwargs: Dict[str, str] = {}
        kwargs["host"] = host
        kwargs["input_path"] = filename

        log.debug(f"built autocomplete function arguments: {kwargs}")
        log.debug(f"requesting function: {self.function}")

        # first try to get the answer from suggestion server
        try:
            client = connect_to_suggestion_server(
                log_level=logging.DEBUG,
                unique_socket_address=unique_socket_address
            )
        except TimeoutError:
            log.debug("switching to serverless suggestion engine")
            return getattr(Completion(), self.function, None)(**kwargs)
        else:
            try:
                # raise OSError
                client.write((self.function, kwargs))
                result = client.read()

            # if suggestion server method fails, revert to direct mode
            except OSError as e:
                log.warning(f"encountered exception when retrieving "
                            f"data from server {e}")

                log.debug("switching to serverless suggestion engine")
                result = getattr(Completion(), self.function, None)(**kwargs)
            else:
                client.close()
            finally:
                return result
