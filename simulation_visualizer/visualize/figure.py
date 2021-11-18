from dash.dependencies import Input, Output, State, ALL

from simulation_visualizer.utils import Context
from .app import app
from typing import List, Union, Dict, TYPE_CHECKING, Tuple, Any
import logging
from .cache import df_cache
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash.exceptions import PreventUpdate


try:
    from typing import Literal  # type: ignore
except ImportError:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from pandas import DataFrame


log = logging.getLogger(__name__)


# TODO implement every n-th row save and plot
@app.callback(
    Output("download", "data"),
    [Input("download-button", "n_clicks"), Input("session-id", "children")],
    [
        State({"type": "select", "index": "x"}, "value"),
        State({"type": "select", "index": "y"}, "value"),
        State({"type": "select", "index": "z"}, "value"),
        State({"type": "select", "index": "t"}, "value"),
        State({"type": "input-host", "index": ALL}, "value"),
        State({"type": "input-path", "index": ALL}, "value"),
        State("dimensionality-state", "value"),
        State("plot-type", "value"),
        State("download-type", "value"),
    ],
    prevent_initial_call=True,
)
def download_data(
    _,
    session_id: str,
    x_select: str,
    y_select: Union[str, List[str]],
    z_select: str,
    t_select: str,
    host: List[str],
    path: List[str],
    dimension: Literal["2D", "3D"],
    plot_type: str,
    download_type: str,
) -> Dict[str, str]:

    log.info(f"requested download type is: {download_type}")

    df = df_cache(path, host, session_id)

    if download_type == "csv":
        return {
            "content": df.to_csv(),
            "filename": "data.csv",
            "mimetype": "text/csv",
        }
    elif download_type == "html":
        fig = get_fig(
            df, x_select, y_select, z_select, t_select, plot_type, dimension, host, path
        )
        return {
            "content": fig.to_html(include_plotlyjs="cdn"),
            "filename": "data.html",
            "mimetype": "text/html",
        }


@app.callback(
    [
        Output("plot-graph", "figure"),
        Output("plot-graph-max", "figure"),
        Output("plot-error", "children"),
    ],
    [Input("plot-button-state", "n_clicks"), Input("session-id", "children")],
    [
        State({"type": "select", "index": "x"}, "value"),
        State({"type": "select", "index": "y"}, "value"),
        State({"type": "select", "index": "z"}, "value"),
        State({"type": "select", "index": "t"}, "value"),
        State({"type": "input-host", "index": ALL}, "value"),
        State({"type": "input-path", "index": ALL}, "value"),
        State("dimensionality-state", "value"),
        State("plot-type", "value"),
    ],
    prevent_initial_call=True,
)
def update_figure(
    plot_clicks,
    session_id: str,
    x_select: str,
    y_select: Union[str, List[str]],
    z_select: str,
    t_select: str,
    host: List[str],
    path: List[str],
    dimension: Literal["2D", "3D"],
    plot_type: str,
) -> Tuple[Any, Any, str]:

    print(dash.callback_context.triggered[0]["prop_id"].split(".")[0])
    log.info(f"update_figure() triggered by: {Context().id} , plot_clicks: {plot_clicks}")
    log.debug(f"update_figure got paths: {path}")
    log.debug(f"update_figure got hosts: {host}")

    if any([p is None for p in path]):
        raise PreventUpdate()

    df = df_cache(path, host, session_id)

    if not isinstance(df, Exception):

        fig = get_fig(
            df, x_select, y_select, z_select, t_select, plot_type, dimension, host, path
        )
        warning = ""
    else:
        fig = dash.no_update
        files = ",".join([f"{h}@{p}" for h, p in zip(host, path)])
        warning = f"Couln't read {files}.\nError: {df}"
        log.warning(warning)

    log.debug("figure ready, sending to user session")
    return fig, fig, warning


def get_fig(
    df: "DataFrame",
    x_select: str,
    y_select: str,
    z_select: str,
    t_select: str,
    plot_type: str,
    dimension: str,
    host: List[str],
    path: List[str],
) -> Any:

    # surface cannot be done with plotly express
    if plot_type == "surface":
        fig = go.Figure(data=[go.Surface(z=df.values)])
    else:
        plot = getattr(px, plot_type)

        if len(host) <= 1:
            title = f"Plotting file: {host[0]}@{path[0]}"
        else:
            files = ",".join([f"{h}@{p}" for h, p in zip(host, path)])
            title = f"Plotting files: {files}"

        kwargs = dict(x=x_select, y=y_select, title=title)
        if dimension.startswith("3D"):
            kwargs["z"] = z_select
        if dimension.endswith("series"):
            kwargs["animation_frame"] = t_select
        # TODO animation group

        fig = plot(df, **kwargs)

    return fig
