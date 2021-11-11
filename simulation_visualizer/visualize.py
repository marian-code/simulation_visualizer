import logging
import re
from atexit import register as register_exit_hook
from pathlib import Path
from shutil import rmtree
from socket import gethostname
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import dash
import dash_auth
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import ALL, MATCH, Input, Output, State
from dash.exceptions import PreventUpdate
from dash_extensions.enrich import ServersideOutput
from flask_caching import Cache
from ssh_utilities import Connection
from typing_extensions import Literal

from simulation_visualizer.layout import serve_layout
from simulation_visualizer.parser import DataExtractor
from simulation_visualizer.path_completition import Suggest
from simulation_visualizer.utils import get_auth, get_file_size, get_root, sizeof_fmt
try:
    from typing import TypedDict  # type: ignore
except ImportError:
    from typing_extensions import TypedDict

if TYPE_CHECKING:
    _DS = Dict[str, str]
    _LDS = List[_DS]
    _HOST_DATA = TypedDict("_HOST_DATA", {"path": str, "host": str})
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
SUGGESTION_SOCKET = "/tmp/user-{}-id-{}-suggestion_server"
USER_LIST = get_auth()
# expected address is: https://simulate.duckdns.org.visualize
APACHE_URL_SUBDIR = get_root()

HOSTS = [{"label": h, "value": h} for h in Connection.get_available_hosts()]
HOSTS.append(
    {"label": f"{gethostname().lower()}-local", "value": gethostname().lower()}
)

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
        State("x-select", "value"),
        State("y-select", "value"),
        State("z-select", "value"),
        State("t-select", "value"),
        State({"type": "input-host", "index": ALL}, "value"),
        State({"type": "input-path", "index": ALL}, "value"),
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
    host: List[str],
    path: List[str],
    dimension: Literal["2D", "3D"],
    plot_type: str,
) -> Tuple[Any, Any, str]:

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


@cache.memoize(timeout=600)
def df_cache(path: List[str], host: List[str], session_id: str):
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


# TODO split this monstrosity!
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
    ],
    prevent_initial_call=True,
)
def update_axis_select(
    _,
    url: str,
    session_id: str,
    host: List[str],
    path: List[str],
    addressbar_sw: bool,
    plot_clicks: int,
) -> Tuple[
    "_LDS",
    "_LDS",
    "_LDS",
    "_LDS",
    str,
    str,
    str,
    str,
    str,
    "_DS",
    str,
    str,
    bool,
    int,
    int,
]:

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
    if len(host) == 1:
        filesize_msg = f"File size is: {sizeof_fmt(byte_size)}"
    else:
        filesize_msg = f"Combined size of all files is: {sizeof_fmt(byte_size)}"

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
        # must be at least of length 1, and upon init it is 0
        host = [dash.no_update] * max(len(host), 1)
        path = [dash.no_update] * max(len(host), 1)
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
    x_select: str,
    y_select: List[str],
    z_select: List[str],
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


@app.callback(
    [
        Output("url-path", "pathname"),
        Output("url-path", "hash"),
    ],
    [
        Input({"type": "path-store", "index": ALL}, "data"),
    ],
    [State("url-path", "href")],
    prevent_initial_call=False,
)
def update_ulr(host_data: "_HOST_DATA", href: str) -> Tuple[str, str]:

    log.debug(f"url href: {href}")

    filenames = [hd["path"] for hd in host_data]
    hosts = [hd["host"] for hd in host_data]

    for i, filename in enumerate(filenames):

        # when running through apache in https://simulate.duckdns.org/visualize
        # this is needed because dash will overwrite the subdir component
        if APACHE_URL_SUBDIR in href and not filename.startswith(
            f"/{APACHE_URL_SUBDIR}"
        ):
            filename = f"/{APACHE_URL_SUBDIR}{filename}"

        filenames[i] = filename

    filename = "|".join(filenames)
    host = "#" + "|".join(hosts)

    return filename, host


# TODO we would like to output path into input-path here, so we can shorten it when
# TODO it is wrong for some reason. But it is already taken
# TODO by other callback - update_axis_select
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


# TODO trigger re-submit to load new cols upon remove
# TODO color delete button in red when last element is to be removed
@app.callback(
    Output("control-tab", "children"),
    [Input("add-button", "n_clicks"), Input("remove-button", "n_clicks")],
    State("control-tab", "children"),
    prevent_initial_call=False,
)
def change_host(n_clicks: int, _, tab: List[Any]) -> List[Any]:
    event_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]

    print("event_id", event_id)

    if event_id in ("add-button", ""):
        return add_host(n_clicks, tab)
    else:
        #return tab
        return remove_host(tab)


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
        id=f"path-selector-{n_clicks}"
    )

    tab.insert(1, selector)
    return tab


def remove_host(tab: List[Any]) -> List[Any]:
    log.info("preparing to delete path selector")
    # not all elements have ids
    ids = []
    for element in tab:
        if "props" in element:
            if "id" in element["props"]:
                ids.append(element["props"]["id"])
    log.debug(f"found elements ids: {ids}")

    n_selectors = sum(["path-selector" in i for i in ids])
    log.debug(f"found {n_selectors} path selector elements")

    # delete from the last inserted
    if n_selectors > 1:
        for index, i in reversed(enumerate(ids)):
            if "path-selector" in i:
                del tab[index]
                log.info("succesfully deleted one path selector")
                break
    else:
        log.warning("only one path selector is left, we cannot delete that")

    return tab


# TODO check if paths for more files are parsed correctly, they probably are not
def parse_url(url: str):

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
            dim = "2D"

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

        # split host and filenames  which are separated by delimiter '|'
        host = host.split("|")
        filename = filename.split("|")
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
