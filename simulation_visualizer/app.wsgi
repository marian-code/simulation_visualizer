import sys

from logging.config import fileConfig
import logging
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from visualize import app

# this sets up logs when apache2 runs the wsgi app
logging.getLogger("paramiko").setLevel(logging.ERROR)
logging.getLogger("ssh_utilities").setLevel(logging.ERROR)
logging.getLogger("watchdog").setLevel(logging.ERROR)
fileConfig(HERE / "logs" / "log_config.ini", disable_existing_loggers=False)

application = app.server
