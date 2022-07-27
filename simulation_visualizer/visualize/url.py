import logging
import re

import dash
from dash.exceptions import PreventUpdate
from .app import app, APACHE_URL_SUBDIR
from typing import List, Tuple, TYPE_CHECKING
from dash.dependencies import ALL, Input, Output, State

try:
    from typing import TypedDict, Literal  # type: ignore
except ImportError:
    from typing_extensions import TypedDict, Literal

if TYPE_CHECKING:
    _HOST_DATA = TypedDict("_HOST_DATA", {"path": str, "host": str})

log = logging.getLogger(__name__)


@app.callback(
    [Output("url-path", "search")],
    [
        Input({"type": "select", "index": "x"}, "value"),
        Input({"type": "select", "index": "y"}, "value"),
        Input({"type": "select", "index": "z"}, "value"),
        Input({"type": "select", "index": "t"}, "value"),
        Input("dimensionality-state", "value"),
    ],
    prevent_initial_call=True,
)
def update_url_select(
    x_select: str,
    y_select: List[str],
    z_select: List[str],
    t_select: List[str],
    dim: Literal["2D", "2D-series", "3D", "3D-series"],
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



# TODO check if paths for more files are parsed correctly, they probably are not
def parse_url(url: str):

    URL_NUM = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d*"
    URL_STR = r".*?/visualize"
    URL_LOC = r"localhost:\d+"
    # find string or ip address
    URL = r"https?://(?:" + URL_NUM + r"|" + URL_STR + r"|" + URL_LOC + r")"
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
    log.debug(R"re string is:" + URL + DATA)

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
        log.debug(f"parsed host: {host}")
        log.debug(f"parsed filename: {filename}")

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
        hosts = host.split("|")
        filenames = filename.split("|")
        return hosts, filenames, x_select, y_select, z_select, t_select, dim
