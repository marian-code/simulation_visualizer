import sys

from logging.config import fileConfig
import logging
from pathlib import Path

PKG_ROOT = Path(__file__).parent
sys.path.insert(0, str(PKG_ROOT))
from utils import set_root
set_root("visualize")
from visualize import app

# this sets up logs when apache2 runs the wsgi app
logging.getLogger("paramiko").setLevel(logging.ERROR)
logging.getLogger("ssh_utilities").setLevel(logging.ERROR)
logging.getLogger("watchdog").setLevel(logging.ERROR)
fileConfig(PKG_ROOT / "logs" / "log_config.ini", disable_existing_loggers=False)

application = app.server
