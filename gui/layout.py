import dash_bootstrap_components as dbc

from portal_utils import ThemeDropDown
from dash_view import Builder

# Set the light and dark themes of your app here

THEMES = {'lux': dbc.themes.LUX, 'darkly': dbc.themes.DARKLY}


def make_layout():
    context = Builder.load_file('layout.kv')
    context.arguments.update(context.imports)
    layout = Builder.build_layout(context.layout, context.arguments, context.style)

    # The theme changer component. If you want to move the dropdown, you can, but the component must be in the app.
    theme_selector = ThemeDropDown(id='theme', options=THEMES)

    # It is strongly recommended that you leave this code, modifying only above.
    # The Container and Location along with the update_theme in the callbacks.py
    # allow for the app to respond to theme changes that come from the PSL Portal (when embedded)
    return dbc.Container([theme_selector, layout], id='root', fluid=True, className="dbc")
