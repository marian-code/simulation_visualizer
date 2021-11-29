import concurrent.futures as cf
import logging
from itertools import product
from os.path import basename, commonpath
from typing import TYPE_CHECKING, List, Optional, Tuple, Union, overload

import pandas as pd
from rapidfuzz import fuzz
from typing_extensions import Literal

try:
    from typing import TypedDict  # type: ignore
except ImportError:
    from typing_extensions import TypedDict

from .parsers import load_parsers
from ..utils import DifferentFileError, all_equal, timeit
from .parser_meta import FileParser

if TYPE_CHECKING:
    from pandas import DataFrame

    SUGGEST = TypedDict(
        "SUGGEST", {"x": List[int], "y": List[int], "z": List[int], "t": List[int]}
    )

log = logging.getLogger(__name__)

MAX_PARSE_ATTEMPTS: int = 3


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

    def __init__(self, paths: List[str], hosts: List[str], session_id: str) -> None:

        load_parsers()
        self.parsers = FileParser.parsers
        log.debug(f"got parsers: {', '.join([str(p) for p in self.parsers])}")

        self._paths = paths
        self._hosts = hosts
        self._session_id = session_id

    # TODO implement file hint to force select parser
    def extract(
        self, *, mode: Literal["merge", "parallel"]
    ) -> Union["DataFrame", Exception]:
        with timeit("file read"):

            data = self._get_async("data", self._hosts, self._paths)

            if isinstance(data, Exception):
                return data
            elif len(self._hosts) <= 1:
                return data[0]
            elif mode == "merge":
                # check if we have the same columns
                cols = (d.columns.values.tolist() for d in data)
                if all_equal(cols) > 1:
                    return DifferentFileError(
                        f"dataframes do not contain same columns: {cols}"
                    )

                # add one more column with filename that will differentiate datasets
                common = f"{commonpath(self._paths)}/"
                for d, p in zip(data, self._paths):
                    p = p.replace(common, "")  # replace leading common path
                    p = p.replace(f"/{basename(p)}", "")  # replace filename
                    d["color"] = p

                return pd.concat(data)

            elif mode == "parallel":
                return pd.concat([d.reindex(data[0].index) for d in data], axis=1)

    def header(
        self, *, mode: Literal["merge", "parallel"]
    ) -> Union[Tuple[List[str], "SUGGEST"], Exception]:

        headers = self._get_async("header", self._hosts, self._paths)

        if isinstance(headers, Exception):
            return headers
        elif len(self._hosts) <= 1:
            return headers[0]
        elif mode == "merge":
            if all_equal(headers) == 1:
                return headers[0]
            else:
                return DifferentFileError(f"files {self._paths} are not of same type")
        else:
            cols = [h for header in headers for h in header[0]]
            # TODO this we can copy x from first and in the others we can shift
            # TODO column numbers by the numer of entries in previous lists
            suggest = headers[0][1]

            return cols, suggest

    @overload
    def _get_async(
        self, what: Literal["header"], host: List[str], path: List[str]
    ) -> Union[List[Tuple[List[str], "SUGGEST"]], Exception]:
        ...

    @overload
    def _get_async(
        self, what: Literal["data"], host: List[str], path: List[str]
    ) -> Union[List["DataFrame"], Exception]:
        ...

    def _get_async(self, what, hosts, paths):

        # indexer is essentially transposed array (hosts, paths) it is a list of
        # 2-tuples. We index the futures dict by matching tuples
        indexer: List[Tuple[str, str]] = list(zip(hosts, paths))
        # create combinations of all parsers to all host-file combinations
        # this is a list of tuple elements: (parser, (host, path))
        targets = list(product(self.parsers, indexer))
        # now sort in such order that combinations that are more likely to parse
        # successfully are submited first
        targets.sort(
            key=lambda x: fuzz.ratio(x[0].expected_filename, x[1][1]), reverse=True
        )

        with cf.ThreadPoolExecutor(max_workers=len(self.parsers)) as executor:

            # create the futures
            future_to_df = {
                executor.submit(self._get_one, parser, what, host, path): (host, path)
                for parser, (host, path) in targets
            }

            # initialize empy list for results, we must store results in order
            # with which the requests came in
            datas = [None] * len(hosts)

            # collect the results
            for future in cf.as_completed(future_to_df):

                data, error = future.result()
                if error is None:
                    # get index of hte future - the 2-tuple: (host, path)
                    idx = indexer.index(future_to_df[future])
                    datas[idx] = data

                    # count woth work with DataFrames present in list
                    if not any([d is None for d in datas]):
                        executor.shutdown(wait=False)
                        return datas

            # if loop has not exited, that means all results where errors,
            # so we return the last one
            log.exception(f"None of the data parsers could extract {paths}")
            return error

    @overload
    def _get_one(
        self, parser: FileParser, what: Literal["header"], host: str, path: str
    ) -> Tuple[Optional[Exception], Optional[Tuple[List[str], "SUGGEST"]]]:
        ...

    @overload
    def _get_one(
        self, parser: FileParser, what: Literal["data"], host: str, path: str
    ) -> Tuple[Optional[Exception], Optional["DataFrame"]]:
        ...

    def _get_one(self, parser, what, host, path):

        log.debug(f"trying {what} parser: {parser}")

        if not parser.can_handle(path, host):
            return None, Exception
        else:
            parser.set_session_id(self._session_id)

        error = None
        for i in range(1, MAX_PARSE_ATTEMPTS + 1):

            try:
                data = getattr(parser, f"extract_{what}", None)(path, host)
            except FileNotFoundError as e:
                log.warning(e)
                error = e
            except Exception as e:
                log.exception(e)
                error = e
            else:
                log.debug(f"{what} parsed successfully: {path} after {i} attempts")
                return data, None

        log.warning(f"{what} parser {parser} failed to extract {path}")
        return None, error
