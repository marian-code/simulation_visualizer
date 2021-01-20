import logging
import re
from atexit import register as register_exit_hook
from pathlib import Path
from shutil import rmtree
from simulation_visualizer.text import PLUGINS_INTRO, URL_SHARING, USAGE
from socket import gethostname
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union
from uuid import uuid4

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_extensions import Download
from flask_caching import Cache
from ssh_utilities import Connection
from typing_extensions import Literal

from simulation_visualizer.parser import DataExtractor
from simulation_visualizer.path_completition import Suggest
from simulation_visualizer.utils import get_file_size, input_parser, sizeof_fmt

if TYPE_CHECKING:
    _DS = Dict[str, str]
    _LDS = List[_DS]
    from pandas import DataFrame


log = logging.getLogger(__name__)

SERVER_HOST = "0.0.0.0"
SERVER_PORT = "8050"

EXTERNAL_STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
PARSERS = {
    str(p.name): p.description for p in DataExtractor("", "", "").parsers
}
HOSTS = [{"label": h, "value": h} for h in Connection.get_available_hosts()]
HOSTS.append(
    {"label": f"{gethostname().lower()}-local", "value": gethostname().lower()}
)

CACHEFILE = mkdtemp(prefix="sim_visualizer_cache_")
CACHE_CONFIG = {
    "CACHE_TYPE": "filesystem",
    "CACHE_DIR": CACHEFILE,
    "CACHE_DEFAULT_TIMEOUT": 60,
    #'CACHE_TYPE': 'redis',
    #'CACHE_REDIS_URL': os.environ.get('REDIS_URL', 'redis://localhost:6379')
}
SUGGESTION_SOCKET = "/tmp/user-{}-suggestion_server"

register_exit_hook(rmtree, CACHEFILE)

app = dash.Dash(__name__, external_stylesheets=EXTERNAL_STYLESHEETS)
app.title = "Simulation visualizer"

cache = Cache()
cache.init_app(app.server, config=CACHE_CONFIG)


def serve_layout():
    session_id = str(uuid4())

    plot = [
        dcc.Loading(
            id="loading-plot",
            type="default",
            children=[html.Div(dcc.Graph(id="plot-graph"))],
        ),
        html.P(id="plot-error", style={"color": "red"}),
    ]

    plot_max = [
        dcc.Loading(
            id="loading-plot-max",
            type="default",
            children=[
                html.Div(
                    dcc.Graph(
                        id="plot-graph-max",
                        style={"width": "95vw", "height": "80vh"},
                    )
                )
            ],
        )
    ]

    tab_1 = [
        dcc.Location(id="url-path", refresh=False),
        html.Datalist(id="list-paths", children=[]),
        # * select file and server controls
        html.Div(
            [
                html.Div(
                    [
                        html.Label("Select host PC"),
                        dcc.Dropdown(
                            id="input-host",
                            options=HOSTS,
                            value="kohn",
                        ),
                    ],
                    className="six columns",
                ),
                html.Div(
                    [
                        html.Label("Select path to file"),
                        dcc.Input(
                            id="input-path",
                            type="text",
                            placeholder="/full/path/to/file",
                            style={"width": "100%"},
                            list="list-paths",
                        ),
                    ],
                    className="six columns",
                ),
            ],
            className="row",
        ),
        html.Div(id="show-path"),
        html.Button(id="submit-button", n_clicks=0, children="Submit"),
        html.Div(id="show-filesize"),
        html.Hr(),
        html.H3(children="Graph controls"),
        html.Div(
            [
                # * left column with graph controls
                html.Div(
                    [
                        dcc.RadioItems(
                            id="dimensionality-state",
                            options=[
                                {"label": "2D", "value": "2D"},
                                {"label": "3D", "value": "3D"},
                            ],
                            value="2D",
                        ),
                        html.Label("Select x axis"),
                        dcc.Loading(
                            id="loading-x_select",
                            type="default",
                            children=[
                                html.Div(
                                    dcc.Dropdown(id="x-select", options=[])
                                )
                            ],
                        ),
                        html.Label("Select y axis"),
                        dcc.Loading(
                            id="loading-y-select",
                            type="default",
                            children=[
                                html.Div(
                                    dcc.Dropdown(
                                        id="y-select", options=[], multi=True
                                    )
                                )
                            ],
                        ),
                        html.Label(
                            "Select z axis",
                            id="z-axis-label",
                            style={"display": "none"},
                        ),
                        dcc.Loading(
                            id="loading-z-select",
                            type="default",
                            style={"display": "none"},
                            children=[
                                html.Div(
                                    dcc.Dropdown(
                                        id="z-select",
                                        options=[],
                                        style={"display": "none"},
                                    )
                                )
                            ],
                        ),
                        html.Label("Select plot type"),
                        dcc.Loading(
                            id="loading-y-plot-type",
                            type="default",
                            children=[
                                html.Div(
                                    dcc.Dropdown(
                                        id="plot-type",
                                        options=[
                                            {"label": "line", "value": "line"},
                                            {
                                                "label": "scatter",
                                                "value": "scatter",
                                            },
                                            {
                                                "label": "histogram",
                                                "value": "histogram",
                                            },
                                            {"label": "bar", "value": "bar"},
                                        ],
                                        value="line",
                                    )
                                )
                            ],
                        ),
                        html.Button(
                            id="plot-button-state", n_clicks=0, children="Plot"
                        ),
                        html.Label(
                            "Download data (please dissable any blockers or "
                            "download will not work)"
                        ),
                        dcc.Dropdown(
                            id="download-type",
                            options=[
                                {"label": "csv", "value": "csv"},
                                {"label": "interactive html", "value": "html"},
                            ],
                            value="csv",
                        ),
                        html.Button("Download", id="download-button"),
                        dcc.Loading(
                            id="loading-y-download",
                            type="default",
                            children=[Download(id="download")],
                        ),
                    ],
                    className="one-third column",
                ),
                # * right column with graph and progressbar
                html.Div(plot, className="two-thirds column"),
            ],
            className="row",
        ),
        html.Hr(),
        html.P(
            children=f"Currently available parsers are: "
            f"{', '.join(PARSERS.keys())}"
        ),
        html.Div(id="addressbar-sw", children=True, style={"display": "none"}),
    ]

    tab_2 = [
        html.Div(plot_max),
    ]

    tab_3 = html.Div(
        children=[
            html.P(
                children="Here you will find details about usage of this dashboard."
            ),
            html.Div(
                children=[
                    html.Div(
                        children=[
                            html.H3(children="Parsers"),
                            html.Hr(),
                            html.P(children=PLUGINS_INTRO),
                            html.Div(
                                children=[
                                    html.Div(
                                        children=[
                                            html.H6(children=name),
                                            html.P(
                                                children=desc,
                                                style={"text-indent": "15px"},
                                            ),
                                        ]
                                    )
                                    for name, desc in PARSERS.items()
                                ]
                            ),
                        ],
                        className="six columns",
                    ),
                    html.Div(
                        children=[
                            html.H3(children="Url sharing"),
                            html.Hr(),
                            html.P(
                                children=URL_SHARING,
                                style={"text-indent": "15px"},
                            ),
                            html.H3(children="Usage"),
                            html.Hr(),
                            html.P(
                                children=USAGE,
                                style={"text-indent": "15px"},
                            ),
                        ],
                        className="six columns",
                    ),
                ]
            ),
        ],
    )

    return html.Div(
        children=[
            html.H1(children="Simulation visualizer"),
            html.P(
                children="A Dash web application for displaying progress of simulations."
            ),
            html.Div(session_id, id="session-id", style={"display": "none"}),
            dcc.Tabs(
                [
                    dcc.Tab(
                        label="Controls",
                        children=tab_1,
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                    dcc.Tab(
                        label="Fullscreen Graph",
                        children=tab_2,
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                    dcc.Tab(
                        label="Manual",
                        children=tab_3,
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                ],
                parent_className="custom-tabs",
                className="custom-tabs-container",
            ),
        ]
    )


app.layout = serve_layout


# TODO implement every n-th row save and plot
@app.callback(
    Output("download", "data"),
    [Input("download-button", "n_clicks"), Input("session-id", "children")],
    [
        State("x-select", "value"),
        State("y-select", "value"),
        State("z-select", "value"),
        State("input-host", "value"),
        State("input-path", "value"),
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
    host: str,
    path: str,
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
            df, x_select, y_select, z_select, plot_type, dimension, host, path
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
    host: str,
    path: str,
    dimension: Literal["2D", "3D"],
    plot_type: str,
) -> Tuple[Any, str]:

    if not path:
        raise PreventUpdate()

    df = df_cache(path, host, session_id)

    if not isinstance(df, Exception):

        fig = get_fig(
            df, x_select, y_select, z_select, plot_type, dimension, host, path
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

        if dimension == "2D":
            fig = plot(
                df,
                x=x_select,
                y=y_select,
                title=f"Plotting file: {host}@{path}",
            )
        else:  # 3D
            fig = plot(
                df,
                x=x_select,
                y=y_select,
                z=z_select,
                title=f"Plotting file: {host}@{path}",
            )

    return fig


@app.callback(
    [
        Output("x-select", "options"),
        Output("y-select", "options"),
        Output("z-select", "options"),
        Output("x-select", "value"),
        Output("y-select", "value"),
        Output("z-select", "value"),
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
) -> Tuple[
    "_LDS", "_LDS", "_LDS", str, str, str, str, "_DS", str, str, bool, int, int
]:

    if not dash.callback_context.triggered:
        raise PreventUpdate("No trigering event")

    event_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
    if event_id == "url-path" and not addressbar_sw:
        raise PreventUpdate()
    elif event_id == "url-path" and addressbar_sw:
        host, path, x_sel, y_sel, z_sel, dim = parse_url(url)
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
        x_select,
        y_select,
        z_select,
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
        Input("dimensionality-state", "value"),
    ],
    prevent_initial_call=True,
)
def update_url_select(
    x_select: str, y_select: List[str], z_select: List[str], dim: str
) -> List[str]:

    if x_select:
        search = [f"?x={x_select}"]
    else:
        search = ["?"]
    if y_select:
        search.extend([f"y={y}" for y in y_select])
    if z_select:
        search.extend([f"z={z}" for z in z_select])
    search.extend([f"dim={dim}"])
    search = "&".join(search)

    return [search]


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
    prevent_initial_call=False,
)
def suggest_path(host: str, filename: str, session_id: str):

    if not filename:
        filename = ""

    log.info(f"unique user session id is: {session_id}")

    dirs = Suggest("get_dirs")(
        host, filename, SUGGESTION_SOCKET.format(session_id)
    )

    return [html.Option(value=d) for d in dirs], filename, f"#{host}"


def parse_url(url: str):
    URL = r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d*"
      # negative lookahed ensures that we match the last one #
    DATA = r"(.*?)\?(.*?)#(?!.*#)(.*)"
    URL_FIND = re.compile(URL + DATA)
    PARAM_FIND = r"{}=(\S*?)(?:&|\Z)"

    log.debug(f"parsing url: {url}")

    try:
        filename, search, host = URL_FIND.findall(url)[0]
    except IndexError:
        log.warning("could not parse url")
        raise PreventUpdate()
    else:
        # parse string of type "?x=time&y=u_cn&y=cn&z=u_vol&dim=2D"
        x_select = re.findall(PARAM_FIND.format("x"), search)
        y_select = re.findall(PARAM_FIND.format("y"), search)
        z_select = re.findall(PARAM_FIND.format("z"), search)
        try:
            dim = re.findall(PARAM_FIND.format("dim"), search)[0]
        except IndexError:
            log.warning("could not parse dimension from url, defaulting to 2")
            dim = 2

        log.debug(f"found in url: x:{x_select}, y:{y_select}, z:{z_select}")
        log.debug(f"dimension is: {dim}")

        if (dim == "2D" and all((x_select, y_select))) or (
            dim == "3D" and all((x_select, y_select, z_select))
        ):
            x_select = x_select[0]
        else:
            x_select = dash.no_update
            y_select = dash.no_update
            z_select = dash.no_update
            dim = dash.no_update

            log.warning("Could not parse all parameters from url")

        return (host, filename, x_select, y_select, z_select, dim)


@app.callback(
    [
        Output("y-select", "multi"),
        Output("z-select", "style"),
        Output("z-axis-label", "style"),
        Output("loading-z-select", "style"),
        Output("plot-type", "options"),
    ],
    [Input("dimensionality-state", "value")],
    prevent_initial_call=True,
)
def toggle_z_axis(
    toggle_value: str,
) -> Tuple[bool, "_DS", "_DS", "_DS", "_LDS"]:

    if toggle_value == "2D":
        multiselect_y = True
        visible = {"display": "none"}
        plot_type = [
            {"label": "line", "value": "line"},
            {"label": "scatter", "value": "scatter"},
            {"label": "histogram", "value": "histogram"},
            {"label": "bar", "value": "bar"},
        ]
    else:
        multiselect_y = False  # disable multiselect for 3D
        visible = {"display": "block"}
        plot_type = [
            {"label": "line", "value": "line_3d"},
            {"label": "scatter", "value": "scatter_3d"},
            {"label": "heatmap", "value": "density_heatmap"},
            {"label": "contour", "value": "density_contour"},
            {"label": "histogram", "value": "histogram"},
            {"label": "bar", "value": "bar"},
            {"label": "surface", "value": "surface"},
        ]

    return multiselect_y, visible, visible, visible, plot_type


def main():
    """Toplevel visualizer function."""
    log_level = (5 - input_parser()["log_level"]) * 10

    if log_level == 0:
        lib_level = 10
        log_level = 10
    else:
        lib_level = 30

    logging.getLogger("paramiko").setLevel(lib_level)
    logging.getLogger("ssh_utilities").setLevel(lib_level)
    logging.getLogger("watchdog").setLevel(lib_level)

    logging.basicConfig(
        handlers=[
            logging.FileHandler(filename="logs/sim_visualizer.log", mode="w"),
            logging.StreamHandler(),
        ],
        level=log_level,
        format="[%(asctime)s] %(levelname)-7s " "%(name)-45s %(message)s",
    )

    # delete old suggestiion server logs
    log.info("removing old suggestion server logs")
    for p in (Path(__file__).parent / "logs").glob("suggestion_server*"):
        p.unlink()

    app.run_server(
        debug=True,
        host=SERVER_HOST,
        processes=10,
        threaded=False,
        port=SERVER_PORT,
    )


if __name__ == "__main__":
    main()
