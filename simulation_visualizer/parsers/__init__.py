import importlib
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def load_parsers():

    log.debug("loading parsers")

    for module in Path(__file__).parent.glob("*"):
        if module.stem == "__init__" or module.suffix not in (".py", ".pyc"):
            continue

        try:
            importlib.import_module(f".{module.stem}", __name__)
        except ImportError:
            log.warning(f"failed to load plugin {module.name}, module is "
                        f"not ready for production. Once ready, remove "
                        f"ImportError exception raise statement")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    load_parsers()