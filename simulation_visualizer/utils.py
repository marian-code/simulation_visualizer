import argparse
import logging
import os
from configparser import ConfigParser
from contextlib import contextmanager
from functools import wraps
from itertools import groupby
from json import loads
from json.decoder import JSONDecodeError
from pathlib import Path
from socket import gethostname
from time import time
from typing import Any, Callable, Dict, Iterable, List

import dash
from pbs_wrapper.settings import CONFIG_DIR, MODULE_DIR
from ssh_utilities import Connection

log = logging.getLogger(__name__)

TOOLTIP_STYLE = {
    "background-color": "white",
    "border": "2px solid dodgerblue",
    "border-radius": "10px",
    "padding": "5px",
}


def get_file_size(paths: List[str], hosts: List[str]) -> float:
    sizes = 0
    # group files on same host to make filesize check more efficient
    for host, group in groupby(zip(hosts, paths), lambda x: x[0]):
        local = True if host == gethostname().lower() else False
        with Connection(host, local=local, quiet=True, allow_agent=True) as c:
            for _, path in group:
                sizes += c.os.stat(path).st_size

    return sizes


def sizeof_fmt(num: float, suffix: str = "B") -> str:
    for unit in ("", "K", "M", "G", "T", "P", "E", "Z"):
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Y", suffix)


def timeit(what: str) -> Callable:
    def timing_decorator(function: Callable) -> Callable:
        @wraps(function)
        def decorator(*args, **kwargs):
            t0 = time()
            result = function(*args, **kwargs)
            log.debug(f"{what} execution time: {time() - t0:.2f}s")
            return result
        return decorator
    return timing_decorator

def input_parser() -> Dict[str, int]:

    p = argparse.ArgumentParser(
        description="Dash server app for plotting progress of simulations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    p.add_argument(
        "-v",
        "--verbose",
        default=0,
        action="count",
        dest="log_level",
        help="set verbosity level 1 - 4, 4=EXCEPTION and 1=DEBUG, "
        "5=DEBUG for libraries too",
    )
    p.add_argument(
        "-e",
        "--encrypt",
        default=False,
        action="store_true",
        help="whether to run over ssl secured https or only http. "
        "If secure connection is chosen the certificate will be "
        "generated ad-hoc by Flask, so the site will appear to "
        "user as one with invalid certificate",
    )
    p.add_argument(
        "-p", "--port", default="8050", type=str, help="specify port for the dashboard"
    )

    return vars(p.parse_args())


def get_auth() -> Dict[str, str]:
    text = (Path(__file__).parent / "data/users.txt").read_text().splitlines()
    return {line.split(":")[0]: line.split(":")[1] for line in text}


def set_root(root: str):
    return (Path(__file__).parent / "data/root_doc.txt").write_text(root)


def get_root() -> str:
    return (Path(__file__).parent / "data/root_doc.txt").read_text().strip()


def get_python() -> Path:
    """Get path of python executable.

    Returns
    -------
    Path
        path pointing to python binary
    """
    p = Path(os.__file__).parents[2] / "bin" / "python"
    log.debug(f"got python path: {p}")
    return p


class DifferentFileError(Exception):
    """Raised when `mode=merge` and files have different headers."""

    ...


def all_equal(iterable: Iterable[Any]) -> bool:
    g = groupby(iterable)
    return next(g, True) and not next(g, False)


class Context:
    def __init__(self) -> None:
        self.triggered = dash.callback_context.triggered
        # e.g.: [{'prop_id': 'add-button.n_clicks', 'value': 1}]
        self.id: str = self.triggered[0]["prop_id"].split(".")[0]
        try:
            did = loads(self.id)
        except JSONDecodeError:
            did = None

        self.dict_id: dict = did


def callback_info(function: Callable) -> Callable:
    @wraps
    def decorator(*args, **kwargs):
        log.info(f"firing callback: {function.__name__} triggered by: {Context().id}")
        return function(*args, **kwargs)

    return decorator


def get_qstat_col_names():
    def _getdict(value):
        if value.endswith(","):
            value = value[:-1] + "}"
        if not value.endswith("}"):
            value = value + "}"
        return loads(value)

    template = "BASE"
    ini = "qstat.ini"

    config = ConfigParser(allow_no_value=True, converters={"dict": _getdict})

    if (CONFIG_DIR / ini).is_file():
        config_file = CONFIG_DIR / ini
        config.read(config_file, encoding="utf-8")
    else:
        # it is not clear whether we will have write access in this directory
        config_file = None
        config.read(MODULE_DIR / "config" / ini)

    try:
        config[template].pop("user_assigned_id")
    except KeyError:
        pass

    return list(config[template].keys())


# column names for qstat
DEFAULT_COL_NAMES = get_qstat_col_names()
