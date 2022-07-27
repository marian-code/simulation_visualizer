import logging
from typing import TYPE_CHECKING, Dict, List, Tuple

import dash
from dash.dependencies import ALL, Input, Output, State
from dash.exceptions import PreventUpdate
from simulation_visualizer.file import DataExtractor
from simulation_visualizer.utils import (
    Context,
    callback_info,
    get_file_size,
    sizeof_fmt,
)

from .app import app
from .url import parse_url

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type: ignore

if TYPE_CHECKING:
    _DS = Dict[str, str]
    _LDS = List[_DS]

# for some reason this is not encompased by simulation_visualizer logger by default
log = logging.getLogger(__name__)


def construct_error_msg(paths: List[str], hosts: List[str], e: Exception) -> str:
    files = ", ".join([f"{h}@{p}" for h, p in zip(hosts, paths)])
    plural = ("", "s", "does", "it") if len(hosts) == 1 else ("s", "", "do", "them")
    msg = (
        f"File{plural[0]}: {files} {plural[2]} not exist. "
        f"Or point{plural[1]} to dir{plural[0]}, "
        f"or you have insufficient permissions to read {plural[3]}. "
        f"Error: {e}"
    )
    return msg


# TODO split this monstrosity!
@app.callback(
    [
        Output({"type": "select", "index": ALL}, "options"),
        Output({"type": "select", "index": "x"}, "value"),
        Output({"type": "select", "index": "y"}, "value"),
        Output({"type": "select", "index": "z"}, "value"),
        Output({"type": "select", "index": "t"}, "value"),
        Output("show-filesize", "children"),
        Output("show-filesize", "style"),
        Output({"type": "input-host", "index": ALL}, "value"),
        # TODO ideally separate input-path from here
        Output({"type": "input-path", "index": ALL}, "value"),
        Output("addressbar-sw", "children"),
        Output("dimensionality-state", "value"),
        Output("plot-button-state", "n_clicks"),
    ],
    [
        Input("submit-button", "n_clicks"),
        Input("url-path", "href"),
        Input("session-id", "children"),
    ],
    [
        State({"type": "input-host", "index": ALL}, "value"),
        State({"type": "input-path", "index": ALL}, "value"),
        State("addressbar-sw", "children"),
        State("plot-button-state", "n_clicks"),
        State("file-merge", "value"),
    ],
    prevent_initial_call=True,
)
def update_axis_select(
    _,
    url: str,
    session_id: str,
    hosts: List[str],
    paths: List[str],
    addressbar_sw: bool,
    plot_clicks: int,
    file_merge: Literal["merge", "parallel"],
) -> Tuple[
    List["_LDS"],
    str,
    List[str],
    List[str],
    List[str],
    str,
    "_DS",
    List[str],
    List[str],
    bool,
    Literal["2D", "2D-series", "3D", "3D-series"],
    int,
]:
    context = Context()
    log.info(
        f"update_axis_select() triggered by: {context.id}, "
        f"addressbar_sw is: {addressbar_sw}, plot_clicks: {plot_clicks}"
    )

    if not context.triggered:
        raise PreventUpdate("No trigering event")

    if context.id == "url-path" and not addressbar_sw:
        raise PreventUpdate()
    elif context.id == "url-path" and addressbar_sw:
        hosts, paths, x_sel, y_sel, z_sel, t_sel, dim = parse_url(url)
        addressbar_sw = False

    try:
        data = DataExtractor(paths, hosts, session_id).header(mode=file_merge)
    except FileNotFoundError as e:
        msg = construct_error_msg(paths, hosts, e)
        log.warning(msg)
        NO = [dash.no_update]
        return (NO * 4, *(NO * 4), msg, {"color": "red"}, hosts, paths, *(NO * 3))
    log.debug(f"got axis options: {data}")

    byte_size = get_file_size(paths, hosts)
    if len(hosts) == 1:
        filesize_msg = f"File size is: {sizeof_fmt(byte_size)}"
    else:
        filesize_msg = f"Combined size of all files is: {sizeof_fmt(byte_size)}"

    if byte_size > 1e6:
        filesize_msg += ", plotting and export might take a while"

    log.info(filesize_msg)

    if not isinstance(data, Exception):
        columns, indices = data
        x_select = columns[indices["x"][0]]  # first data column
        y_select = [columns[i] for i in indices["y"]]  # second data column
        z_select = [columns[i] for i in indices["z"]]  # third data colum
        t_select = [columns[i] for i in indices["t"]]  # fourth data colum
        options = [{"label": col, "value": col} for col in columns]
        style = {}
    else:
        x_select = ""
        y_select = [""]
        z_select = [""]
        t_select = [""]
        filesize_msg = str(data)
        options = []
        style = {"color": "red"}

    if context.id == "url-path":
        if x_sel != dash.no_update and y_sel != dash.no_update:
            x_select = x_sel
            y_select = y_sel
            z_select = z_sel
            t_select = t_sel
            plot_clicks += 1
        else:
            plot_clicks = dash.no_update
    else:
        # must be at least of length 1, and upon init it is 0
        hosts = [dash.no_update] * max(len(hosts), 1)
        paths = [dash.no_update] * max(len(hosts), 1)
        dim = dash.no_update
        addressbar_sw = dash.no_update
        plot_clicks = dash.no_update

    print("---------------------------------------------------------------------------")
    from pprint import pprint

    pprint(
        (
            [options] * 4,
            x_select,
            y_select,
            z_select,
            t_select,
            filesize_msg,
            style,
            hosts,
            paths,
            addressbar_sw,
            dim,
            plot_clicks,
        )
    )
    print("---------------------------------------------------------------------------")

    return (
        [options] * 4,
        x_select,
        y_select,
        z_select,
        t_select,
        filesize_msg,
        style,
        hosts,
        paths,
        addressbar_sw,
        dim,
        plot_clicks,
    )


@app.callback(
    [
        Output({"type": "select", "index": "y"}, "multi"),
        Output({"type": "select", "index": "z"}, "style"),
        Output("z-axis-label", "style"),
        Output("loading-z-select", "style"),
        Output({"type": "select", "index": "t"}, "style"),
        Output("t-axis-label", "style"),
        Output("loading-t-select", "style"),
        Output("plot-type", "options"),
    ],
    [Input("dimensionality-state", "value")],
    prevent_initial_call=True,
)
def toggle_z_axis(
    toggle_value: Literal["2D", "2D-series", "3D", "3D-series"],
) -> Tuple[bool, "_DS", "_DS", "_DS", "_DS", "_DS", "_DS", "_LDS"]:

    if toggle_value.startswith("2D"):
        multiselect_y = True
        visible_z = {"display": "none"}
        plot_type = [
            {"label": "line", "value": "line"},
            {"label": "scatter", "value": "scatter"},
            {"label": "histogram", "value": "histogram"},
            {"label": "bar", "value": "bar"},
        ]
    else:
        multiselect_y = False  # disable multiselect for 3D
        visible_z = {"display": "block"}
        plot_type = [
            {"label": "line", "value": "line_3d"},
            {"label": "scatter", "value": "scatter_3d"},
            {"label": "heatmap", "value": "density_heatmap"},
            {"label": "contour", "value": "density_contour"},
            {"label": "histogram", "value": "histogram"},
            {"label": "bar", "value": "bar"},
            {"label": "surface", "value": "surface"},
        ]

    if toggle_value.endswith("series"):
        visible_t = {"display": "block"}
    else:
        visible_t = {"display": "none"}

    return (
        multiselect_y,
        visible_z,
        visible_z,
        visible_z,
        visible_t,
        visible_t,
        visible_t,
        plot_type,
    )
