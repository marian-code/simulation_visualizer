import logging
from contextlib import contextmanager
from socket import gethostname
from time import time
from typing import Dict

from ssh_utilities import Connection
import argparse

log = logging.getLogger(__name__)


def get_file_size(path: str, host: str) -> float:

    local = True if host == gethostname().lower() else False

    with Connection(host, local=local, quiet=True) as c:
        return c.os.stat(path).st_size


def sizeof_fmt(num: float, suffix: str = 'B') -> str:
    for unit in ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'):
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Y', suffix)


@contextmanager
def timeit(what: str):
    t0 = time()
    try:
        yield
    finally:
        log.debug(f"{what} execution time: {time() - t0:.2f}s")


def input_parser() -> Dict[str, int]:

    p = argparse.ArgumentParser(
        description="Dash server app for plotting progress of simulations",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    p.add_argument("-v", "--verbose", default=0, action="count", dest="log_level",
                   help="set verbosity level 1 - 4, 4=EXCEPTION and 1=DEBUG, "
                   "5=DEBUG for libraries too")

    return vars(p.parse_args())