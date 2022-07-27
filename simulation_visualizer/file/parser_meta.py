import abc
import logging
from contextlib import contextmanager
from pathlib import Path
from socket import gethostname
from tempfile import TemporaryDirectory
from typing import IO, TYPE_CHECKING, List, Optional, Tuple
from io import SEEK_END

from ssh_utilities import Connection

try:
    from typing import TypedDict, final  # type: ignore
except ImportError:
    from typing_extensions import TypedDict, final


if TYPE_CHECKING:
    from re import Pattern

    from pandas import DataFrame

    SUGGEST = TypedDict(
        "SUGGEST", {"x": List[int], "y": List[int], "z": List[int], "t": List[int]}
    )

log = logging.getLogger(__name__)


class ParserMount(type):
    """Registers new Parsers."""

    def __init__(cls, name, bases, attrs):
        """Add base class to list of parsers."""
        if not hasattr(cls, "parsers"):
            cls._parsers = []
            log.debug("Created Parser Meta Class")
        else:
            cls._parsers.append(cls)
            log.debug(f'Registered Parser "{name}"')

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
    expected_filename: str = "GENERIC"
    parsers: List["FileParser"]
    session_id: str

    @final
    @classmethod
    @contextmanager
    def _file_opener(  # type: ignore
        cls, host, path, fileobj: Optional[IO] = None, copy_method: bool = False
    ) -> IO:

        local = True if host == gethostname().lower() else False

        if fileobj:
            log.debug("using passed in file object")
            try:
                yield fileobj
            finally:
                pass  # this is a ontext manager requirement
        else:
            if copy_method:
                with Connection(host, local=local, allow_agent=True, quiet=True) as c:
                    with TemporaryDirectory() as td:
                        c.shutil.copy(path, td, direction="get")
                        with (Path(td) / Path(path).name).open("r") as fileobj:
                            try:
                                yield fileobj
                            finally:
                                pass  # this is a context manager requirement
            else:
                log.debug("opening new file object")
                with Connection(host, local=local, allow_agent=True, quiet=True) as c:
                    with c.builtins.open(path, "r") as fileobj:
                        try:
                            yield fileobj
                        finally:
                            pass  # this is a ontext manager requirement

    @classmethod
    def get_n_lines(
        cls,
        path: str,
        host: str,
        fileobj: Optional[IO] = None,
        n_from_end: Optional[int] = None
    ) -> int:

        with cls._file_opener(path, host, fileobj) as f:
            f.seek(0, SEEK_END)
            # find n_from_end line
            # size of line = len(line.encode("utf-8"))
            # open connection and get size of file on disk os.path.getsize(f)
            # appprox_n_lines = file_size / line_size

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
        carefull!
        It is also advisable to make the check fast as you don not want to wait
        long for load
        """
        with cls._file_opener(host, path) as f:

            #look for header on the first 100 lines
            for _ in range(100):
                line = f.readline()

                if cls.header.match(line):
                    log.info(f"parser {cls} can handle {Path(path).name} file type")
                    return True

            log.warning(f"parser {cls} cannot handle {Path(path).name} file type")
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
        return {"x": [0], "y": [1], "z": [2], "t": [0]}

    @abc.abstractclassmethod
    def extract_header(
        cls, path: str, host: str, fileobj: Optional[IO] = None
    ) -> Tuple[List[str], "SUGGEST"]:
        """Return a list with column names."""
        raise NotImplementedError

    @abc.abstractclassmethod
    def extract_data(
        cls, path: str, host: str, fileobj: Optional[IO] = None
    ) -> "DataFrame":
        """Return a pandas dataframe for parsed file."""
        raise NotImplementedError

    def __str__(self):
        return f"<Parser {self.name}>"
