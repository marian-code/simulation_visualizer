from socket import gethostname
from uuid import uuid4

from dash import dcc
from dash import html
from dash_extensions import Download
from ssh_utilities import Connection

from simulation_visualizer.parser import DataExtractor
from simulation_visualizer.text import PLUGINS_INTRO, URL_SHARING, USAGE

HOSTS = [{"label": h, "value": h} for h in Connection.get_available_hosts()]
HOSTS.append(
    {"label": f"{gethostname().lower()}-local", "value": gethostname().lower()}
)
PARSERS = {str(p.name): p.description for p in DataExtractor("", "", "").parsers}


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
                                {"label": "2D-series", "value": "2D-series"},
                                {"label": "3D", "value": "3D"},
                                {"label": "3D-series", "value": "3D-series"},
                            ],
                            value="2D",
                            labelStyle={'display': 'inline-block'},
                        ),
                        html.Label("Select x axis"),
                        dcc.Loading(
                            id="loading-x_select",
                            type="default",
                            children=[
                                html.Div(dcc.Dropdown(id="x-select", options=[]))
                            ],
                        ),
                        html.Label("Select y axis"),
                        dcc.Loading(
                            id="loading-y-select",
                            type="default",
                            children=[
                                html.Div(
                                    dcc.Dropdown(id="y-select", options=[], multi=True)
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
                                        id="t-select",
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
            children=f"Currently available parsers are: " f"{', '.join(PARSERS.keys())}"
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
