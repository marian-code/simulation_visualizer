import logging
from typing import List, Tuple

from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash
from pbs_wrapper import qstat
from simulation_visualizer.utils import DEFAULT_COL_NAMES

"""
from .app import app

log = logging.getLogger(__name__)


# TODO polish this
# TODO allow for deleting jobs
# TODO allow jump to job dir from table
# TODO check why this callback produces error
# TODO if tab-id is not qstat-tab, ideally prevent update, but this does not work
# TODO for some magic reason, when this is active GUI cannot switch to Qstat tab
@app.callback(
    [Output("pbs-table", "columns"), Output("pbs-table", "data")],
    [
        Input("table-cols", "value"),
        Input("app-tabs", "value"),
        Input("pbs-update-timer", "n_intervals"),
    ],
    prevent_initial_call=False,
)
def pbs_updater(cols: List[str], tab_id: str, *args):

    # if tab_id != "qstat-tab":
    #    raise PreventUpdate

    log.info(f"got cols for qstat: {cols}")

    if not cols:
        cols = DEFAULT_COL_NAMES

    rows = qstat([], [], [], [], force_update=True)

    columns = [{"name": k, "id": k} for k in cols]
    return columns, rows


@app.callback(
    [
        Output("qstat-update-message", "children"),
        Output("pbs-update-timer", "interval"),
    ],
    Input("qstat-interval", "value"),
    prevent_initial_call=False,
)
def pbs_set_interval(interval: int) -> Tuple[str, int]:
    log.debug(f"setting new interval: {interval}s")
    msg = f"Table is automatically updated every {interval} seconds."
    return msg, interval * 1000  # convert to miliseconds
"""