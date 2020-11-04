import logging
from socket import gethostname
from typing import TYPE_CHECKING, Dict, List, Union

from ssh_utilities import Connection

from simulation_visualizer.suggestion_server.client import \
    connect_to_suggestion_server

if TYPE_CHECKING:
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
        # open connection to host
        if not self._c:
            self._c = Connection.get(host.lower(), local=local, quiet=True)
        # if host changed establish new connection
        elif self._c.server_name != host.upper():
            self._c.close()
            self._c = Connection.get(host.lower(), local=local, quiet=True)

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

        if path.is_file():
            return [str(path)]

        while True:

            if path.is_dir():
                dirs_files = [d for d in self.c(host).pathlib.Path(path).glob("*")]
                break
            else:
                path = path.parent

        paths = []
        for d in dirs_files:
            if d.is_dir():
                paths.append(f"{d}/")
            else:
                paths.append(str(d))

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

    def __call__(self, host: str, filename: str, unique_socket_address: str
                 ) -> List[str]:
        """Proxy for autocompleter methods.

        Parameters
        ----------
        parser : str
            name of the hsot server
        prefix : str
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
        client = connect_to_suggestion_server(
            log_level=logging.DEBUG,
            unique_socket_address=unique_socket_address
        )

        try:
            # raise OSError
            client.write((self.function, kwargs))
            result = client.read()

        # if suggestion server method fails, revert to direct mode
        except OSError as e:
            log.error(f"encountered exception when retrieving "
                      f"data from server {e}")

            log.debug("switching to serverless suggestion engine")
            result = getattr(Completion(), self.function, None)(**kwargs)
        finally:
            # client.close()
            return result
