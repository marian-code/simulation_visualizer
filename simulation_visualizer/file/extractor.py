from collections import defaultdict
import concurrent.futures as cf
from fileinput import filename
import logging
from itertools import product
from os.path import basename, commonpath
from typing import TYPE_CHECKING, Generator, List, Optional, Tuple, Union, overload

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

    DF_COLS = List[str]
    SUGGEST = TypedDict(
        "SUGGEST", {"x": List[int], "y": List[int], "z": List[int], "t": List[int]}
    )

log = logging.getLogger(__name__)

MAX_PARSE_ATTEMPTS: int = 3


class CannotHandleException(Exception):
    """Raised when parser cannot handle supplied file."""

    pass


# TODO maybe add index column
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
    @timeit("file read")
    def extract(
        self, *, mode: Literal["merge", "parallel"]
    ) -> Union["DataFrame", Exception]:
        """Extract data from remote table file(s).

        Parameters
        ----------
        mode: Literal["merge", "parallel"]
            `merge` mode assumes same format files and merges then into one dataset
            data from different files are then plotted with different colors.
            `parallel` takes different file formats as input and merges all into one
            dataset with columns from all files

        Returns
        -------
        Union["DataFrame", Exception]
            If extraction is successful than a pandas.Dataframe with all columns is
            returned
            If extraction is not succesfull than the causing exception is returned.
        """
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
            for d, n in zip(data, self._get_diff_names()):
                d["color"] = n

            return pd.concat(data)

        elif mode == "parallel":
            df = pd.concat([d.reindex(data[0].index) for d in data], axis=1)
            # grouping same columns taking max value, if more files are loaded
            # it happens that some have same named columns
            return df.groupby(level=0, axis=1).max()

    def header(
        self, *, mode: Literal["merge", "parallel"]
    ) -> Union[Tuple["DF_COLS", "SUGGEST"], Exception]:
        """Extract header(s) from remote table file(s).

        Parameters
        ----------
        mode: Literal["merge", "parallel"]
            `merge` mode assumes same format files and merges then into one dataset
            data from different files are then plotted with different colors.
            `parallel` takes different file formats as input and merges all into one
            dataset with columns from all files

        Returns
        -------
        Union[Tuple["DF_COLS", "SUGGEST"], Exception]
            If extraction is successful than a 2-tuple is returned. First element is
            just a list of column names and the second is dict with list of
            suggestions for each axis.
            If extraction is not succesfull than the causing exception is returned.
        """

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
            columns: "DF_COLS" = []
            suggest: "SUGGEST" = {"x": [0], "y": [0], "z": [0], "t": [0]}
            shift = 0
            for i, (df_cols, df_sugg) in enumerate(headers):
                columns.extend(df_cols)
                if i == 0:
                    suggest = df_sugg.copy()
                else:
                    # we shift the column suggestions by the number of columns in the
                    # previous dataframe(s)
                    suggest["y"].extend([s + shift for s in df_sugg["y"]])
                shift += len(df_cols)

            return sorted(list(set(columns))), suggest

    def _get_diff_names(self) -> Generator[str, None, None]:
        """Get shortest possible distinct names from list of paths.

        Returns
        -------
        List[str]
            distinct names
        """
        common = f"{commonpath(self._paths)}/"
        for p in self._paths:
            p = p.replace(common, "")  # replace leading common path
            yield p.replace(f"/{basename(p)}", "")  # replace filename

    @overload
    def _get_async(
        self, what: Literal["header"], host: List[str], path: List[str]
    ) -> Union[List[Tuple["DF_COLS", "SUGGEST"]], Exception]:
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

            # initialize empty list for results, we must store results in order
            # with which the requests came in
            datas = [None] * len(hosts)

            # collect errors
            errors = defaultdict(set)

            # collect the results
            for future in cf.as_completed(future_to_df):
                # get data
                data = future.result()
                # get index of the future - the 2-tuple: (host, path)
                idx = indexer.index(future_to_df[future])
                if not isinstance(data, Exception):
                    datas[idx] = data

                    # count woth work with DataFrames present in list
                    if not any([d is None for d in datas]):
                        executor.shutdown(wait=False)
                        return datas
                elif isinstance(data, CannotHandleException):
                    pass
                else:
                    errors[future_to_df[future]].add(data)

            # if loop has not exited, that means all results where errors,
            # so we return the last one
            log.warning(
                f"Data parsers were unable to extract "
                f"{sum([1 for d in datas if d is not None])}/{len(datas)} "
                f"path(s) due to errors"
            )

            for (host, filename), error in errors.items():
                log.exception(f" - {host}@{basename(filename):20} -> {error}")
            return CannotHandleException("Data parsers were unable to handle files")

    @overload
    def _get_one(
        self, parser: FileParser, what: Literal["header"], host: str, path: str
    ) -> Union[Tuple["DF_COLS", "SUGGEST"], Exception]:
        ...

    @overload
    def _get_one(
        self, parser: FileParser, what: Literal["data"], host: str, path: str
    ) -> Union["DataFrame", Exception]:
        ...

    def _get_one(self, parser, what, host, path):

        log.debug(f"trying {what} parser: {parser}")

        if not parser.can_handle(path, host):
            return CannotHandleException()
        else:
            parser.set_session_id(self._session_id)

        for i in range(1, MAX_PARSE_ATTEMPTS + 1):

            try:
                data = getattr(parser, f"extract_{what}", None)(path, host)
            except FileNotFoundError as e:
                log.warning(e)
                data = e
            except Exception as e:
                log.exception(e)
                data = e
            else:
                log.debug(f"{what} parsed successfully: {path} after {i} attempts")
                break
        else:
            log.warning(f"{what} parser {parser} failed to extract {path}")

        return data
