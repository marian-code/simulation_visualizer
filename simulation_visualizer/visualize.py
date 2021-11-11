import logging
import re
from atexit import register as register_exit_hook
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import dash
import dash_auth
import plotly.express as px
import plotly.graph_objects as go
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from flask_caching import Cache
from typing_extensions import Literal

from simulation_visualizer.layout import serve_layout
from simulation_visualizer.parser import DataExtractor
from simulation_visualizer.path_completition import Suggest
from simulation_visualizer.utils import get_auth, get_file_size, get_root, sizeof_fmt

if TYPE_CHECKING:
    _DS = Dict[str, str]
    _LDS = List[_DS]
    from pandas import DataFrame

# for some reason this is not encompased by simulation_visualizer logger by default
log = logging.getLogger(f"simulation_visualizer.{__name__}")

EXTERNAL_STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]

CACHEFILE = mkdtemp(prefix="sim_visualizer_cache_")
CACHE_CONFIG = {
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": CACHEFILE,
    "CACHE_DEFAULT_TIMEOUT": 60,
    #'CACHE_TYPE': 'redis',
    #'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
}
SUGGESTION_SOCKET = "/tmp/user-{}-suggestion_server"
USER_LIST = get_auth()
# expected address is: https://simulate.duckdns.org.visualize
APACHE_URL_SUBDIR = get_root()

register_exit_hook(rmtree, CACHEFILE)

app = dash.Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    requests_pathname_prefix=f"/{APACHE_URL_SUBDIR}/" if APACHE_URL_SUBDIR else "/",
)
app.title = "Simulation visualizer"
auth = dash_auth.BasicAuth(app, USER_LIST)
cache = Cache()
cache.init_app(app.server, config=CACHE_CONFIG)
app.layout = serve_layout


# TODO implement every n-th row save and plot
@app.callback(
    Output("download", "data"),
    [Input("download-button", "n_clicks"), Input("session-id", "children")],
    [
        State("x-select", "value"),
        State("y-select", "value"),
        State("z-select", "value"),
        State("t-select", "value"),
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
        State("x-select", "value"),
        State("y-select", "value"),
        State("z-select", "value"),
        State("t-select", "value"),
        State("input-host", "value"),
        State("input-path", "value"),
        State("dimensionality-state", "value"),
        State("plot-type", "value"),
    ],
    prevent_initial_call=True,
)
def update_figure(
    _,
    session_id: str,
    x_select: str,
    y_select: Union[str, List[str]],
    z_select: str,
    t_select: str,
    dimension: Literal["2D", "3D"],
    plot_type: str,
) -> Tuple[Any, str]:

    if not path:
        raise PreventUpdate()

    df = df_cache(path, host, session_id)

    if not isinstance(df, Exception):

        fig = get_fig(
            df, x_select, y_select, z_select, t_select, plot_type, dimension, host, path
        )
        warning = ""
    else:
        fig = dash.no_update
        warning = f"Couln't read {host}@{path}.\nError: {df}"

    log.debug("figure ready, sending to user session")
    return fig, fig, warning


@cache.memoize(timeout=600)
def df_cache(path: str, host: str, session_id: str):
    log.debug("dataframe not cached yet")
    print("dataframe not cached yet")
    return DataExtractor(path, host, session_id).extract()


def get_fig(
    df: "DataFrame",
    x_select: str,
    y_select: str,
    z_select: str,
    t_select: str,
    plot_type: str,
    dimension: str,
    host: str,
    path: str,
) -> Any:

    # surface cannot be done with plotly express
    if plot_type == "surface":
        fig = go.Figure(data=[go.Surface(z=df.values)])
    else:
        plot = getattr(px, plot_type)

        kwargs = dict(x=x_select, y=y_select, title=f"Plotting file: {host}@{path}")
        if dimension.startswith("3D"):
            kwargs["z"] = z_select
        if dimension.endswith("series"):
            kwargs["animation_frame"] = t_select
        # TODO animation group

        fig = plot(df, **kwargs)

    return fig


@app.callback(
    [
        Output("x-select", "options"),
        Output("y-select", "options"),
        Output("z-select", "options"),
        Output("t-select", "options"),
        Output("x-select", "value"),
        Output("y-select", "value"),
        Output("z-select", "value"),
        Output("t-select", "value"),
        Output("show-filesize", "children"),
        Output("show-filesize", "style"),
        Output("input-host", "value"),
        Output("input-path", "value"),
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
        State("input-host", "value"),
        State("input-path", "value"),
        State("addressbar-sw", "children"),
        State("plot-button-state", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def update_axis_select(
    _,
    url: str,
    session_id: str,
    host: str,
    path: str,
    addressbar_sw: bool,
    plot_clicks: int,
) -> Tuple["_LDS", "_LDS", "_LDS", str, str, str, str, "_DS", str, str, bool, int, int]:

    if not dash.callback_context.triggered:
        raise PreventUpdate("No trigering event")

    event_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    if event_id == "url-path" and not addressbar_sw:
        raise PreventUpdate()
    elif event_id == "url-path" and addressbar_sw:
        host, path, x_sel, y_sel, z_sel, t_sel, dim = parse_url(url)
        addressbar_sw = False

    try:
        data = DataExtractor(path, host, session_id).header()
    except FileNotFoundError:
        raise PreventUpdate(
            "File does not exist or path points to dir or you "
            "have insufficient permissions to read it"
        )
    log.debug(f"got axis options: {data}")

    byte_size = get_file_size(path, host)
    filesize_msg = f"File size is: {sizeof_fmt(byte_size)}"

    if byte_size > 1e6:
        filesize_msg += ", plotting and export might take a while"

    log.info(filesize_msg)

    if not isinstance(data, Exception):
        labels, indices = data
        x_select = labels[indices["x"][0]]  # first data column
        y_select = [labels[i] for i in indices["y"]]  # second data column
        z_select = [labels[i] for i in indices["z"]]  # third data colum
        t_select = [labels[i] for i in indices["t"]]  # third data colum
        options = [{"label": l, "value": l} for l in labels]
        style = {}
    else:
        x_select = ""
        y_select = [""]
        z_select = [""]
        filesize_msg = str(data)
        options = []
        style = {"color": "red"}

    if event_id == "url-path":
        if x_sel != dash.no_update and y_sel != dash.no_update:
            x_select = x_sel
            y_select = y_sel
            z_select = z_sel
            t_select = t_sel
            plot_clicks += 1
        else:
            plot_clicks = dash.no_update
    else:
        host = dash.no_update
        path = dash.no_update
        dim = dash.no_update
        addressbar_sw = dash.no_update
        plot_clicks = dash.no_update

    return (
        options,
        options,
        options,
        options,
        x_select,
        y_select,
        z_select,
        t_select,
        filesize_msg,
        style,
        host,
        path,
        addressbar_sw,
        dim,
        plot_clicks,
    )


@app.callback(
    [Output("url-path", "search")],
    [
        Input("x-select", "value"),
        Input("y-select", "value"),
        Input("z-select", "value"),
        Input("t-select", "value"),
        Input("dimensionality-state", "value"),
    ],
    prevent_initial_call=True,
)
def update_url_select(
    t_select: List[str],
    dim: str,
) -> List[str]:

    if x_select:
        search = [f"?x={x_select}"]
    else:
        search = ["?"]
    if y_select:
        search.extend([f"y={y}" for y in y_select])
    if z_select:
        search.extend([f"z={z}" for z in z_select])
    if t_select:
        search.extend([f"t={t}" for t in t_select])
    search.extend([f"dim={dim}"])
    search_str = "&".join(search)

    return [search_str]


@app.callback(
    Output("show-path", "children"),
    [Input("input-host", "value"), Input("input-path", "value")],
    prevent_initial_call=True,
)
def update_output(host: str, filename: str):
    return f"Selected file is: {host}@{filename}"


@app.callback(
    [
        Output("list-paths", "children"),
        Output("url-path", "pathname"),
        Output("url-path", "hash"),
    ],
    [
        Input("input-host", "value"),
        Input("input-path", "value"),
        Input("session-id", "children"),
    ],
    [State("url-path", "href")],
    prevent_initial_call=False,
)
def suggest_path(host: str, filename: Optional[str], session_id: str, href: str):

    if not filename:
        filename = ""

    log.debug(f"url pathname: {filename}")
    log.info(f"unique user session id is: {session_id}")

    dirs = Suggest("get_dirs")(
        host, filename, Path(SUGGESTION_SOCKET.format(session_id))
    )

    log.debug(f"url href: {href}")

    # when running through apache in https://simulate.duckdns.org/visualize
    # this is needed because dash will overwrite the subdir component
    if APACHE_URL_SUBDIR in href and not filename.startswith(f"/{APACHE_URL_SUBDIR}"):
        filename = f"/{APACHE_URL_SUBDIR}{filename}"

    return [html.Option(value=d) for d in dirs], filename, f"#{host}"


def parse_url(url: str):
    # URL = r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d*"
    # DATA = r"(.*?)\?(.*?)#(?!.*#)(.*)"

    URL_NUM = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d*"
    URL_STR = r".*?/visualize"
    # find string or ip address
    URL = r"https?://(?:" + URL_NUM + r"|" + URL_STR + r")"
    # string component that can contain special characters ending with question mark,
    # may or may not be present
    PATH_COMP = r"(?:(\S*?)\?|/)?"
    # parameters component 2-string with '=' and '&' symbols
    # with 0 or more occurences
    PARAM_COMP = r"((?:\S+=\S+&?){0,})"
    # server component is just a plain string
    # negative lookahed ensures that we match the last one '#'
    SERVER_COMP = r"#(?!.*#)(.*)"
    DATA = PATH_COMP + PARAM_COMP + SERVER_COMP
    URL_FIND = re.compile(URL + DATA)
    PARAM_FIND = r"{}=(\S*?)(?:&|\Z)"

    log.debug(f"parsing url: {url}")

    try:
        data = URL_FIND.findall(url)[0]
    except IndexError:
        log.warning("could not parse url")
        raise PreventUpdate()
    else:
        if len(data) == 3:
            filename, search, host = data
        else:
            _, host = data
            # TODO ################################################
            # TODO visualize component in url is getting overwritten
            filename = ""
            search = ""

        # parse string of type "?x=time&y=u_cn&y=cn&z=u_vol&dim=2D"
        x_select = re.findall(PARAM_FIND.format("x"), search)
        y_select = re.findall(PARAM_FIND.format("y"), search)
        z_select = re.findall(PARAM_FIND.format("z"), search)
        t_select = re.findall(PARAM_FIND.format("t"), search)
        try:
            dim = re.findall(PARAM_FIND.format("dim"), search)[0]
        except IndexError:
            log.warning("could not parse dimension from url, defaulting to 2")
            dim = 2

        log.debug(f"found in url: x:{x_select}, y:{y_select}, z:{z_select}")
        log.debug(f"dimension is: {dim}")

        if (dim.startswith("2D") and all((x_select, y_select))) or (
            dim.startswith("3D") and all((x_select, y_select, z_select))
        ):
            x_select = x_select[0]
        else:
            x_select = dash.no_update
            y_select = dash.no_update
            z_select = dash.no_update
            t_select = dash.no_update
            dim = dash.no_update

            log.warning("Could not parse all parameters from url")

        return (host, filename, x_select, y_select, z_select, t_select, dim)


@app.callback(
    [
        Output("y-select", "multi"),
        Output("z-select", "style"),
        Output("z-axis-label", "style"),
        Output("loading-z-select", "style"),
        Output("t-select", "style"),
        Output("t-axis-label", "style"),
        Output("loading-t-select", "style"),
        Output("plot-type", "options"),
    ],
    [Input("dimensionality-state", "value")],
    prevent_initial_call=True,
)
def toggle_z_axis(
    toggle_value: str,
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
