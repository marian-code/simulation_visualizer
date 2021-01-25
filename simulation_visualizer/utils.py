import logging
from contextlib import contextmanager
from socket import gethostname
from time import time
from typing import Dict
from pathlib import Path

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
    p.add_argument("-e", "--encrypt", default=False, action="store_true",
                   help="whether to run over ssl secured https or only http. "
                   "I secure connection is chosen the certificate will be "
                   "generated ad-hoc by Flask, so the site will appear to "
                   "user as one with invalid certificate")
    p.add_argument("-p", "--port", default="8050", type=str,
                   help="specify port for the dashboard")

    return vars(p.parse_args())


def get_auth() -> Dict[str, str]:

    text = (Path(__file__).parent / "data/users.txt").read_text().splitlines()
    return {line.split(":")[0]: line.split(":")[1] for line in text}
