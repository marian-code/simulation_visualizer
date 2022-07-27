"""
# TODO - subclass output and add new parameters so we can target the store element
# Output({"type": "input-host-store"}, store=True)
# - get the respective Dropdown from app.layout
# - extract its id and based on that create a new id with sub-index
# - all this auto-generated elements will reside in some predefined layout element
#   for easy reference
# - user will be than responsible to target as much indices as are available
#   with his callbacks
# maybe we can add the missing elements auto-magically by extracting
@app.callback(
    [
        Output({"type": "input-host-store", "index": ALL, "sub": 2}, "data"),
    ],
    [
        Input("test-button", "n_clicks"),
    ],
    prevent_initial_call=True
)
def test(_) -> str:
    print("test button clicked")
    return [["aurel"]]


@app.callback(
    [
        Output({"type": "input-host", "index": MATCH}, "value"),
    ],
    [
        Input({"type": "input-host-store", "index": MATCH, "sub": ALL}, "data"),
    ],
    prevent_initial_call=False
)
def merge_input_host(host):
    print("--------------------got host", host)
    print(Context().id)
    return (host[1], )

"""