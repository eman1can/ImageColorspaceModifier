import uuid
from os import listdir
from os.path import join

import plotly.graph_objects as go
from dash import html, Output, Input, State, ALL, callback_context, dcc, ClientsideFunction, callback, MATCH
import dash_bootstrap_components as dbc
from dash_bootstrap_components import DropdownMenu
from dash_bootstrap_templates import template_from_url
from dash.exceptions import PreventUpdate
from dash_view import Builder
from portal_utils import call_api, to_series, to_dataframe


def get_modification_actions():
    return [DropdownMenu(x) for x in ['Invert', 'Offset', 'Clamp', 'Scale', 'Threshold']]


def get_callbacks(app):
    app.clientside_callback(
        """
        function(filenames, contents, current) {
            if (filenames == null) {
                return window.dash_clientside.no_update;
            }
            if (filenames.length == 0) {
                return window.dash_clientside.no_update;
            }
            
            let upload = current[0];
            upload['props']['className'] = 'small-upload';
            current[0] = upload;
            
            for (let ix = 0; ix < filenames.length; ix++) {
                let name = filenames[ix];
                let content = contents[ix];
                
                let box = {
                    'namespace': 'dash_html_components',
                    'type': 'Div',
                    'props': {
                        'className': 'photo-box',
                        'id': name,
                        'children': [
                            {
                                'namespace': 'dash_html_components',
                                'type': 'Img',
                                'props': {
                                    'src': content
                                }
                            },
                            {
                                'namespace': 'dash_html_components',
                                'type': 'Button',
                                'props': {
                                    'id': {'type': 'photo-remove', 'value': name},
                                }
                            }
                        ]
                    }
                };
                
                current.push(box);
            }
            return [current, null];
        }
        """,
        Output('input-photos', 'children'),
        Output('upload-data', 'filename'),
        Input('upload-data', 'filename'),
        Input('upload-data', 'contents'),
        State('input-photos', 'children'),
    )

    app.clientside_callback(
        """
        function(n_clicks, current) {
            let upload = current[0];
            upload['props']['className'] = 'upload';
            let nothing = {
                'namespace': 'dash_html_components',
                'type': 'H2',
                'props': {
                    'children': 'Nothing to Show',
                    'style': {'textAlign': 'center'}
                }
            };
            return [upload, nothing];
        }
        """,
        Output('input-photos', 'children', allow_duplicate=True),
        Output('output-photos', 'children', allow_duplicate=True),
        Input('clear-input', 'n_clicks'),
        State('input-photos', 'children'),
        prevent_initial_call=True
    )

    app.clientside_callback(
        """
            function(children) {
                if (children == null) {
                    return window.dash_clientside.no_update;
                }
                if (children.length == 1) {
                    return {'display': 'none'};
                }
                return {'display': 'block'};
            }
        """,
        Output('clear-input', 'style'),
        Input('input-photos', 'children'),
    )

    app.clientside_callback(
        """
        function(n_clicks, input_current, output_current) {
            let button = window.dash_clientside.callback_context.triggered[0];
            if (button['value'] == null) {
                return window.dash_clientside.no_update;
            }
            
            let photo_id = button['prop_id'].substring(32, button['prop_id'].length - 11);
            if (photo_id == null) {
                return window.dash_clientside.no_update;
            }
            for (let ix = 1; ix < input_current.length; ix++) {
                let child = input_current[ix];
                let child_button = child['props']['children'][1]['props']['id'];
                if (child_button['value'] == photo_id) {
                    input_current.splice(ix, 1);
                    break;
                }
            }
            for (let ix = 0; ix < output_current.length; ix++) {
                let child = output_current[ix];
                let child_button = child['props']['children'][1]['props']['id'];
                if (child_button['value'] == photo_id) {
                    output_current.splice(ix, 1);
                    break;
                }
            }
            
            if (input_current.length == 1) {
                let upload = input_current[0];
                upload['props']['className'] = 'upload';
                input_current[0] = upload;
            }
            
            return [input_current, output_current];
        }
        """,
        Output('input-photos', 'children', allow_duplicate=True),
        Output('output-photos', 'children', allow_duplicate=True),
        Input({'type': 'photo-remove', 'value': ALL}, 'n_clicks'),
        State('input-photos', 'children'),
        State('output-photos', 'children'),
        prevent_initial_call=True
    )

    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="make_draggable"),
        Output("modification-list", "data-drag"),
        [Input("modification-list", "id")],
    )

    app.clientside_callback(
        """
            function(children) {
                if (children == null) {
                    return true;
                }
                if (children.length == 0) {
                    return true;
                }
                return false;
            }
        """,
        Output('clear-modifications', 'disabled'),
        Input('modification-list', 'children'),
    )

    app.clientside_callback(
        """
            function(children) {
                return [];
            }
        """,
        Output('modification-list', 'children', allow_duplicate=True),
        Input('clear-modifications', 'n_clicks'),
        prevent_initial_call=True
    )

    @app.callback(
        Output('modification-list', 'children', allow_duplicate=True),
        Input({'type': 'add-modification', 'value': ALL}, 'n_clicks'),
        State('modification-list', 'children'),
        prevent_initial_call='initial_duplicate'
    )
    def add_modification(n_clicks, current):
        if current is None:
            current = []
        trigger = callback_context.triggered_id
        if trigger is None:
            raise PreventUpdate
        name = trigger['value']
        base_id = uuid.uuid4().hex
        if name == 'Invert':
            child = Builder.build_template(app.ctx, 'ModificationRow', name, base_id)
        elif name == 'Offset':
            child = Builder.build_template(app.ctx, 'ModificationRowNumeric', name, base_id, 'Offset Value')
        elif name == 'Scale':
            child = Builder.build_template(app.ctx, 'ModificationRowNumeric', name, base_id, 'Scale Value')
        elif name == 'Clamp':
            child = Builder.build_template(app.ctx, 'ModificationRowKeywordNumeric', name, base_id, 'Clamp Type', ['Min', 'Max'], 'Clamp Value')
        else:  # Threshold
            child = Builder.build_template(app.ctx, 'ModificationRowNumeric', name, base_id, 'Threshold Value')
        current.append(child)
        return current

    app.clientside_callback(
        """
        function(n_clicks, current) {
            if (current == "Output") {
                return ["No Output", {"backgroundColor": "#ffffff", "color": "#000000", "borderWidth": "3px", "width": "140px"}];
            } else {
                return ["Output", {"backgroundColor": "#000000", "borderWidth": "3px", "width": "140px"}];
            }
        }
        """,
        Output({'type': 'modification-output', 'value': MATCH}, 'children'),
        Output({'type': 'modification-output', 'value': MATCH}, 'style'),
        Input({'type': 'modification-output', 'value': MATCH}, 'n_clicks'),
        State({'type': 'modification-output', 'value': MATCH}, 'children'),
        prevent_initial_call=True
    )

    app.clientside_callback(
        """
        function(n_clicks, current) {
            on_style = {'borderColor': '#32CD32', 'borderWidth': '3px', 'borderStyle': 'solid', 'width': '200px'}
            off_style = {'borderColor': '#CD3232', 'borderWidth': '3px', 'borderStyle': 'solid', 'width': '200px'}
            if (current == "Auto Clamp ON") {
                return ["Auto Clamp OFF", off_style];
            } else {
                return ["Auto Clamp ON", on_style];
            }
        }
        """,
        Output('auto-clamp', 'children'),
        Output('auto-clamp', 'style'),
        Input('auto-clamp', 'n_clicks'),
        State('auto-clamp', 'children'),
        prevent_initial_call=True
    )

    app.clientside_callback(
        """
        function(photos, modifications) {
            if (photos == null || modifications == null) {
                return true;
            }
            return photos.length <= 1 || modifications.length == 0;
        }
        """,
        Output('apply-modifications', 'disabled'),
        Input('input-photos', 'children'),
        Input('modification-list', 'children'),
        prevent_initial_call=True
    )

    def get_widget(b, v, *args):
        if v == -1:
            return b['props']['children']
        elif isinstance(v, str):
            if v in b['props']:
                return b['props'][v]
            return None
        else:
            c = b['props']['children'][v]
            if len(args) > 0:
                return get_widget(c, *args)
            return c

    @app.callback(
        Output('output-photos', 'children'),
        Output('modification-error', 'children'),
        Input('apply-modifications', 'n_clicks'),
        State('input-photos', 'children'),
        State('modification-list', 'children'),
        State('auto-clamp', 'children')
    )
    def apply_modifications(n_clicks, photos, modifications, clamp):
        if n_clicks is None:
            raise PreventUpdate

        operations = {'auto_clamp': clamp == 'Auto Clamp ON', 'input': [], 'operations': [], 'output_format': 'default'}

        for p in photos[1:]:
            src = get_widget(p, 0, 'src')
            name = get_widget(p, 1, 'id')['value']
            print(name)
            # TODO: Get Photo name from id
            operations['input'].append((name, src))

        message = None
        for ixm, m in enumerate(modifications):
            name = get_widget(m, 0, 0, 0, 0, 0, -1).lower()

            operation = {'action': name, 'channels': []}

            for ix in range(4):
                opt = get_widget(m, 0, 0, 2, 0, 0, ix, 0, 1, 'value')
                if opt is not None:
                    operation['channels'] += [x.lower() for x in opt]
            if len(operation['channels']) == 0:
                message = f'Mod ({ixm}): Must select 1 or more channels'

            params = None
            if name in ('offset', 'scale', 'threshold'):
                group = get_widget(m, 0, 0, 4, 1, 0, 0)
                select = get_widget(group, 0, 'value')
                value = get_widget(group, 1, 'value')
                if message is None and (select is None or value is None):
                    message = f'Mod ({ixm}): Must select a value or enter a value or both'
                params = [select, value]
                output = get_widget(m, 0, 0, 6, 0, -1)
            elif name in ('clamp', ):
                keyword = get_widget(m, 0, 0, 4, 1, 0, 0, 'value')
                if message is None and keyword is None:
                    message = f'Mod ({ixm}): Must select a valid clamp type'
                group = get_widget(m, 0, 0, 6, 1, 0, 0)
                select = get_widget(group, 0, 'value')
                value = get_widget(group, 1, 'value')
                params = [keyword, select, value]
                output = get_widget(m, 0, 0, 8, 0, -1)
            else:
                output = get_widget(m, 0, 0, 4, 0, -1)
            operation['params'] = params
            operation['input'] = None
            operation['auto_clamp'] = False
            operation['output_format'] = 'default' if output == 'Output' else None
            operations['operations'].append(operation)

        if message is not None:
            return html.H2('Nothing to Show', style={'textAlign': 'center'}), message

        r = call_api('operations', 'post', operations)
        if r is None:
            message = 'The server failed to generate the output'
            return html.H2('Nothing to Show', style={'textAlign': 'center'}), message

        output = []
        for name, output_list in r.items():
            for output_data in output_list:
                photo = Builder.build_template(app.ctx, 'Photo', name, output_data)
                output.append(photo)
        return output, None
