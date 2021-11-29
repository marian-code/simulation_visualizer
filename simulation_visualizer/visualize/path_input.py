import logging
from pathlib import Path
from socket import gethostname
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import dash
from dash import dcc, html
from dash.dependencies import ALL, MATCH, Input, Output, State
from dash_extensions.enrich import ServersideOutput
from simulation_visualizer.path_completition import Suggest
from simulation_visualizer.utils import Context
from ssh_utilities import Connection

from .app import app

try:
    from typing import TypedDict  # type: ignore
except ImportError:
    from typing_extensions import TypedDict

if TYPE_CHECKING:
    _HOST_DATA = TypedDict("_HOST_DATA", {"path": str, "host": str})

log = logging.getLogger(__name__)

HOSTS = [{"label": h, "value": h} for h in sorted(Connection.get_available_hosts())]
HOSTS.append(
    {"label": f"{gethostname().lower()}-local", "value": gethostname().lower()}
)
SUGGESTION_SOCKET = "/tmp/user-{}-id-{}-suggestion_server"


# TODO trigger re-submit to load new cols upon remove
# TODO color delete button in red when last element is to be removed
@app.callback(
    [
        Output("control-tab", "children"),
        Output("file-merge", "style"),
        Output("file-merge", "value"),
    ],
    [Input("add-button", "n_clicks"), Input("remove-button", "n_clicks")],
    State("control-tab", "children"),
    prevent_initial_call=False,
)
def change_host(n_clicks: int, _, tab: List[Any]) -> Tuple[List[Any], Dict[str, str]]:
    event_id = Context().id

    if event_id in ("add-button", ""):
        shift = 1
        tab = add_host(n_clicks, tab)
    else:
        shift = -1
        tab = remove_host(tab)

    # TODO this is a verid shit after first add we still have one path selector
    # TODO and after first remove the number of found selectors does not change too
    if get_n_selectors(tab)[0] + shift > 1:
        visible = {"display": "block"}
        merge_setting = dash.no_update
    else:
        visible = {"display": "none"}
        merge_setting = "parallel"

    return tab, visible, merge_setting


def add_host(n_clicks: int, tab: List[Any]) -> html.Div:
    selector = html.Div(
        [
            html.Div(
                [
                    html.Label("Select host PC"),
                    dcc.Dropdown(
                        id={"type": "input-host", "index": n_clicks},
                        options=HOSTS,
                        value="kohn",
                    ),
                ],
                className="two columns",
            ),
            html.Div(
                [
                    html.Label("Select path to file"),
                    dcc.Input(
                        id={"type": "input-path", "index": n_clicks},
                        type="text",
                        placeholder="/full/path/to/file",
                        style={"width": "100%"},
                        list=f"list-paths-{n_clicks}",
                    ),
                ],
                className="nine columns",
            ),
            dcc.Store(
                id={"type": "path-store", "index": n_clicks},
                data={"path": "", "host": ""},
            ),
            html.Div(
                id={"type": "list-paths", "index": n_clicks},
                children=html.Datalist(id=f"list-paths-{n_clicks}", children=[]),
                hidden=True,
            ),
        ],
        className="row",
        id=f"path-selector-{n_clicks}",
    )

    tab.insert(1, selector)
    return tab


def remove_host(tab: List[Any]) -> List[Any]:
    log.info("preparing to delete path selector")

    n_selectors, element_ids = get_n_selectors(tab)

    # delete from the last inserted
    if n_selectors > 1:
        for index, e_id in enumerate(element_ids):
            if "path-selector" in e_id:
                del tab[index]
                log.info("succesfully deleted one path selector")
                break
    else:
        log.warning("only one path selector is left, we cannot delete that")

    return tab


def get_n_selectors(tab: List[Any]) -> Tuple[int, List[str]]:

    # not all elements have ids
    element_ids = []
    for element in tab:
        if "props" in element:
            if "id" in element["props"]:
                element_ids.append(element["props"]["id"])
    log.debug(f"found element ids: {element_ids}")

    n_selectors = sum(["path-selector" in i for i in element_ids])
    log.debug(f"found {n_selectors} path selector elements")

    return n_selectors, element_ids


@app.callback(
    Output("show-path", "children"),
    [
        Input({"type": "input-host", "index": ALL}, "value"),
        Input({"type": "input-path", "index": ALL}, "value"),
    ],
    prevent_initial_call=True,
)
def update_output(host: List[str], path: List[str]):
    if len(host) <= 1:
        return f"Selected file is: {host[0]}@{path[0]}"
    else:
        files = ",".join([f"{h}@{p}" for h, p in zip(host, path)])
        return f"Selected files are: {files}"


# TODO upon delete somehow plot button fires and plot tries to update???
# TODO we would like to output path into input-path here, so we can shorten it
# TODO when it is wrong for some reason. But it is already taken by other
# TODO callback - update_axis_select
@app.callback(
    [
        Output({"type": "list-paths", "index": MATCH}, "children"),
        ServersideOutput({"type": "path-store", "index": MATCH}, "data"),
    ],
    [
        Input({"type": "input-host", "index": MATCH}, "value"),
        Input({"type": "input-path", "index": MATCH}, "value"),
        Input({"type": "input-host", "index": MATCH}, "id"),
        Input("session-id", "children"),
    ],
    prevent_initial_call=False,
)
def suggest_path(
    host: str, path: Optional[str], match_id: dict, session_id: str
) -> Tuple[List[html.Datalist], "_HOST_DATA"]:
    if not path:
        path = ""

    log.debug(f"url hostname: {host}")
    log.debug(f"url pathname: {path}")
    log.info(f"unique user session id is: {session_id}")

    path, dirs = Suggest("get_dirs")(
        host, path, Path(SUGGESTION_SOCKET.format(session_id, match_id["index"]))
    )

    # we are outputing a whole Datalist into respective Div children. This is a
    # workaround, because we cannot pass pattern-matching dict id to Input(list=<here>)
    return (
        [
            html.Datalist(
                id=f"list-paths-{match_id['index']}",
                children=[html.Option(value=d) for d in dirs],
            )
        ],
        {"path": path, "host": host},
    )
