import abc
import concurrent.futures as cf
import logging
from contextlib import contextmanager
from pathlib import Path
from socket import gethostname
from tempfile import TemporaryDirectory
from typing import IO, TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from ssh_utilities import Connection
from typing_extensions import Literal

try:
    from typing import final, TypedDict  # python >=3.8 version
except ImportError:
    from typing_extensions import final, TypedDict

from .parsers import load_parsers
from .utils import timeit

if TYPE_CHECKING:
    from re import Pattern

    from pandas import DataFrame

    SUGGEST = TypedDict("SUGGEST", {
        "x": List[int],
        "y": List[int],
        "z": List[int]
    })

log = logging.getLogger(__name__)

MAX_PARSE_ATTEMPTS: int = 5

class ParserMount(type):
    """Registers new Parsers."""

    def __init__(cls, name, bases, attrs):
        """Add base class to list of parsers."""
        if not hasattr(cls, "parsers"):
            cls._parsers = []
            log.debug("Created Parser Meta Class")
        else:
            cls._parsers.append(cls)
            log.debug(f"Registered Parser \"{name}\"")

    @property
    def parsers(cls) -> List["FileParser"]:
        """Read-only attribute containing all available parsers.

        :type: .FileParser
        """
        return cls._parsers

    def __str__(self):
        """Return string rep."""
        return f"<Parser {self.__name__}>"


class FileParser(metaclass=ParserMount):
    """A class capable of retrieving various data formats.

    Since all parsers are subclasses of FileParser, every parser can access
    all other mounted parsers through cls.parsers attribute.

    Additionally both extract methods support passing in file-object so when
    using more methods you can use the same opened file which needs to be
    opened only once.
    """

    name: str = "GENERIC"
    description: str = "Generic parser Class"
    header: "Pattern"
    parsers: List["FileParser"]
    session_id: str

    @final
    @classmethod
    @contextmanager
    def _file_opener(cls, host, path, fileobj: Optional[IO] = None,
                     copy_method: bool = False) -> IO:

        local = True if host == gethostname().lower() else False

        if fileobj:
            log.debug("using passed in file object")
            try:
                yield fileobj
            finally:
                pass
        else:
            if copy_method:
                with Connection(host, local=local, quiet=True) as c:
                    with TemporaryDirectory() as td:
                        c.shutil.copy(path, td, direction="get")
                        with (Path(td) / Path(path).name).open("r") as fileobj:
                            try:
                                yield fileobj
                            finally:
                                pass
            else:
                log.debug("opening new file object")
                with Connection(host, local=local, quiet=True) as c:
                    with c.builtins.open(path, "r") as fileobj:
                        try:
                            yield fileobj
                        finally:
                            pass

    @final
    @classmethod
    def set_session_id(cls, session_id: str):
        cls.session_id = session_id

    @classmethod
    def can_handle(cls, path: str, host: str) -> bool:
        """Check whether this Parser can extract file.

        Now it is based solely on file header, override in subclass to define
        your own behaviour.

        Warnings
        --------
        Defined criteria must always discriminate only one type of file, so be
        carefull
        It is also advisable to make the check fast as you don not want to wait
        long for load
        """

        with cls._file_opener(host, path) as f:
            line = f.readline()

            if cls.header.match(line):
                log.info(f"parser {cls} can handle {Path(path).name} "
                         f"file type")
                return True
            else:
                log.warning(f"parser {cls} cannot handle "
                            f"{Path(path).name} file type")
                return False

    @staticmethod
    def _suggest_axis() -> "SUGGEST":
        """Get default data column index for each axis.

        For 'x' only one index should be specified, if more are present, only
        the first will be used

        Returns
        -------
        "SUGGEST"
            dictionary with data column indices for each axis
        """
        return {"x": [0], "y": [1], "z": [2]}

    @abc.abstractclassmethod
    def extract_header(cls, path: str, host: str,
                       fileobj: Optional[IO] = None) -> Tuple[List[str], "SUGGEST"]:
        """Return a list with column names"""
        raise NotImplementedError

    @abc.abstractclassmethod
    def extract_data(cls, path: str, host: str,
                     fileobj: Optional[IO] = None) -> "DataFrame":
        """Return a pandas dataframe for parsed file."""
        raise NotImplementedError

    def __str__(self):
        return f"<Parser {self.name}>"


class DataExtractor:
    """Class taking care of reading file from remote.

    Parameters
    ----------
    path: str
        the path to file to be read from remote
    host: str
        server name string
    session_id: str
        unique session id string for each user
    """

    parsers: List[FileParser]

    def __init__(self, path: str, host: str, session_id: str) -> None:

        load_parsers()
        self.parsers = FileParser.parsers
        log.debug(f"got parsers: {', '.join([str(p) for p in self.parsers])}")

        self._path = path
        self._host = host
        self._session_id = session_id

    def extract(self) -> Union["DataFrame", Exception]:
        with timeit("file read"):
            return self._get_async("data")

    def header(self) -> Union[Tuple[List[str], "SUGGEST"], Exception]:
        return self._get_async("header")

    def _get_async(self, what: Literal["data", "header"]
                   ) -> Union["DataFrame", Tuple[List[str], "SUGGEST"],
                              Exception]:

        with cf.ThreadPoolExecutor(max_workers=len(self.parsers)) as executor:
            future_to_df = {
                executor.submit(self._get_one, p, what): p for p in self.parsers
            }
            for future in cf.as_completed(future_to_df):

                data, error = future.result()
                if error is None:
                    executor.shutdown(wait=False)
                    return data
            else:
                log.exception(f"None of the data parsers could extract "
                              f"{self._path}")
                return error

    def _get_one(self, parser: FileParser, what: Literal["data", "header"]
                 ) -> Tuple[Optional[Exception],
                            Optional[Union["DataFrame",
                                           Tuple[List[str], "SUGGEST"]]]]:

        log.debug(f"trying {what} parser: {parser}")

        if not parser.can_handle(self._path, self._host):
            return None, Exception
        else:
            parser.set_session_id(self._session_id)

        error = None
        for i in range(1, MAX_PARSE_ATTEMPTS + 1):

            try:
                data = getattr(parser, f"extract_{what}", None)(self._path,
                                                                self._host)
            except FileNotFoundError as e:
                log.warning(e)
                error = e
            except Exception as e:
                log.exception(e)
                error = e
            else:
                log.debug(f"{what} parsed successfully: {self._path} "
                          f"after {i} attempts")
                return data, None
        else:
            log.warning(f"{what} parser {parser} "
                        f"failed to extract {self._path}")
            return None, error
