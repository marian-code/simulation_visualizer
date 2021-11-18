import logging
from atexit import register as register_exit_hook
from shutil import rmtree
from tempfile import mkdtemp
from typing import List

from flask_caching import Cache
from simulation_visualizer.parser import DataExtractor

from .app import app

log = logging.getLogger(__name__)


CACHEFILE = mkdtemp(prefix="sim_visualizer_cache_")
CACHE_CONFIG = {
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": CACHEFILE,
    "CACHE_DEFAULT_TIMEOUT": 60,
    #'CACHE_TYPE': 'redis',
    #'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
}
register_exit_hook(rmtree, CACHEFILE)

cache = Cache()
cache.init_app(app.server, config=CACHE_CONFIG)

@cache.memoize(timeout=600)
def df_cache(path: List[str], host: List[str], session_id: str):
    log.debug("dataframe not cached yet")
    return DataExtractor(path, host, session_id).extract()
