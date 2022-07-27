import logging

import dash
import dash_auth
from simulation_visualizer.layout import serve_layout
from simulation_visualizer.utils import get_auth, get_root
from simulation_visualizer.version import __version__

# for some reason this is not encompased by simulation_visualizer logger by default
log = logging.getLogger(__name__)

# to get grid working
# "https://stackpath.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap-grid.min.css"
EXTERNAL_STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
#import dash_bootstrap_components as dbc
#EXTERNAL_STYLESHEETS = [dbc.themes.COSMO]
USER_LIST = get_auth()
# expected address is: https://simulate.duckdns.org.visualize
APACHE_URL_SUBDIR = get_root()

app = dash.Dash(
    __name__,
    external_stylesheets=EXTERNAL_STYLESHEETS,
    requests_pathname_prefix=f"/{APACHE_URL_SUBDIR}/" if APACHE_URL_SUBDIR else "/",
    title=f"Simulation visualizer - v{__version__}",
)
auth = dash_auth.BasicAuth(app, USER_LIST)
app.layout = serve_layout
