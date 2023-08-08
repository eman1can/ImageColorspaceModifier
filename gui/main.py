from dash import Dash

import dash_bootstrap_components as dbc

from callbacks import get_callbacks
from layout import make_layout

from dash_view import Builder

DEBUG = True

DEFAULT_THEME = dbc.themes.LUX

dbc_css = "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
dragula = "https://epsi95.github.io/dash-draggable-css-scipt/dragula.css"
dragula_js = "https://cdnjs.cloudflare.com/ajax/libs/dragula/3.7.2/dragula.min.js"
dragula_local_js = "https://epsi95.github.io/dash-draggable-css-scipt/script.js"
app = Dash(__name__, suppress_callback_exceptions=True,
           external_stylesheets=[DEFAULT_THEME, dbc_css, dragula],
           external_scripts=[dragula_local_js, dragula_js])
app.ctx = Builder.load_file('layout.kv')
app.layout = make_layout
get_callbacks(app)
server = app.server

if __name__ == "__main__":
    app.run_server(debug=DEBUG, port=8041)
