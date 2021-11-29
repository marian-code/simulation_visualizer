from uuid import uuid4

from dash import dcc
from dash import html
from dash.dash_table import DataTable
from dash_extensions import Download
import dash_bootstrap_components as dbc

from simulation_visualizer.file import DataExtractor
from simulation_visualizer.text import PLUGINS_INTRO, URL_SHARING, USAGE
from pbs_wrapper.settings import TEMPLATE
from simulation_visualizer.utils import DEFAULT_COL_NAMES

PARSERS = {str(p.name): p.description for p in DataExtractor([""], [""], "").parsers}
TOOLTIP_STYLE = {
    "background-color": "white",
    "border": "2px solid dodgerblue",
    "border-radius": "10px",
    "padding": "5px",
}


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
        # * select file and server controls will be dynamically added here
        html.Div(id="show-path"),
        html.Button(id="submit-button", n_clicks=0, children="Submit"),
        dbc.Tooltip(
            "If you have 2 or more files, select merge/parallel mode in "
            "the graph controls menu before submiting.",
            target="submit-button",
            style=TOOLTIP_STYLE,
        ),
        html.Button(id="add-button", n_clicks=0, children="Add host"),
        html.Button(id="remove-button", n_clicks=0, children="Remove host"),
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
                                {"label": "2D-series", "value": "2D-series"},
                                {"label": "3D", "value": "3D"},
                                {"label": "3D-series", "value": "3D-series"},
                            ],
                            value="2D",
                            labelStyle={"display": "inline-block"},
                        ),
                        dbc.Tooltip(
                            "series options add a slider that will represent another "
                            "dimension.",
                            target="dimensionality-state",
                            style=TOOLTIP_STYLE,
                        ),
                        dcc.RadioItems(
                            id="file-merge",
                            options=[
                                {"label": "merge", "value": "merge"},
                                {"label": "parallel", "value": "parallel"},
                            ],
                            value="parallel",
                            labelStyle={"display": "inline-block"},
                            style={"display": "none"},
                        ),
                        dbc.Tooltip(
                            "If you change mode you must click submit again. Merge "
                            "mode requires same files and data from each one is ploted "
                            "with different color. Parallel mode can have files with "
                            "different columns which will be combined into one dataset",
                            target="file-merge",
                            style=TOOLTIP_STYLE,
                        ),
                        html.Label("Select x axis"),
                        dcc.Loading(
                            id="loading-x_select",
                            type="default",
                            children=[
                                html.Div(
                                    dcc.Dropdown(
                                        id={"type": "select", "index": "x"}, options=[]
                                    )
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
                                        id={"type": "select", "index": "y"},
                                        options=[],
                                        multi=True,
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
                                        id={"type": "select", "index": "z"},
                                        options=[],
                                        style={"display": "none"},
                                    )
                                )
                            ],
                        ),
                        html.Label(
                            "Select t axis",
                            id="t-axis-label",
                            style={"display": "none"},
                        ),
                        dcc.Loading(
                            id="loading-t-select",
                            type="default",
                            style={"display": "none"},
                            children=[
                                html.Div(
                                    dcc.Dropdown(
                                        id={"type": "select", "index": "t"},
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
                                {"label": "interactive html", "value": "html"},
                                {"label": "csv", "value": "csv"},
                            ],
                            value="html",
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
            children=f"Currently available parsers are: {', '.join(PARSERS.keys())}"
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

    tab_4 = html.Div(
        children=[
            html.P(children="Table is autoamtically updated every 5 seconds."),
            dcc.Interval(id="pbs-update-timer", interval=5000),
            DataTable(
                id="pbs-table",
                columns=[],
                data={},
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                row_selectable="multi",
                selected_columns=[],
                selected_rows=[],
                page_action="native",
                page_current=0,
                page_size=10,
            ),
            html.P(
                children="Select desired columns "
                "(empty will give you the default selection):"
            ),
            dcc.Dropdown(
                id="table-cols",
                options=[{"label": k, "value": k} for k in TEMPLATE.keys()],
                value=DEFAULT_COL_NAMES,
                multi=True,
            ),
        ]
    )

    return html.Div(
        children=[
            html.H1(children="Simulation visualizer"),
            html.P(
                children="A Dash web application for displaying progress of simulations"
            ),
            html.Div(session_id, id="session-id", style={"display": "none"}),
            dcc.Tabs(
                [
                    dcc.Tab(
                        id="control-tab",
                        value="control-tab",
                        label="Controls",
                        children=tab_1,
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                    dcc.Tab(
                        id="graph-tab",
                        value="graph-tab",
                        label="Fullscreen Graph",
                        children=tab_2,
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                    dcc.Tab(
                        id="manual-tab",
                        value="manual-tab",
                        label="Manual",
                        children=tab_3,
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                    dcc.Tab(
                        id="qstat-tab",
                        value="qstat-tab",
                        label="Qstat",
                        children=tab_4,
                        className="custom-tab",
                        selected_className="custom-tab--selected",
                    ),
                ],
                id="app-tabs",
                value="control-tab",
                parent_className="custom-tabs",
                className="custom-tabs-container",
            ),
        ]
    )
