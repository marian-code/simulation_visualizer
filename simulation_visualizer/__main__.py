import logging
from pathlib import Path

from .utils import input_parser, set_root

SERVER_HOST = "0.0.0.0"
PKG_ROOT = Path(__file__).parent


def main():
    """Toplevel visualizer function."""
    args = input_parser()

    log_level = (5 - args["log_level"]) * 10

    if log_level == 0:
        lib_level = 10
        log_level = 10
    else:
        lib_level = 30

    logging.getLogger("paramiko").setLevel(lib_level)
    logging.getLogger("ssh_utilities").setLevel(lib_level)
    logging.getLogger("watchdog").setLevel(lib_level)

    # ! only for debugging
    #logging.getLogger("simulation_visualizer.suggestion_server").setLevel(lib_level)
    #logging.getLogger("simulation_visualizer.path_completition").setLevel(lib_level)
    #logging.getLogger("simulation_visualizer.parser").setLevel(lib_level)

    logging.basicConfig(
        handlers=[
            logging.FileHandler(
                filename=PKG_ROOT / "logs" / "sim_visualizer.log", mode="w"
            ),
            logging.StreamHandler(),
        ],
        level=log_level,
        format="[%(asctime)s] %(levelname)-7s %(name)-46s|--> %(message)s",
    )

    # delete old suggestiion server logs
    logging.getLogger(__name__).info("removing old suggestion server logs")
    for p in (PKG_ROOT / "logs").glob("suggestion_server*"):
        p.unlink()

    set_root("")

    from .visualize import app

    app.run_server(
        debug=True,
        host=SERVER_HOST,
        processes=10,
        threaded=False,
        port=args["port"],
        ssl_context="adhoc" if args["encrypt"] else None,
    )


if __name__ == "__main__":
    main()
