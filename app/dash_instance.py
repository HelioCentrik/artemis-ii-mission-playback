# app/dash_instance.py
#
# Dash application instance. Imported by main.py (entrypoint) and by page
# modules that need to register callbacks against the app object.
#
# pages_folder="" disables auto-discovery. Pages are imported explicitly in
# main.py after this module is fully initialised — no circular import risk.
#
# assets_folder is absolute because __name__ here is "app.dash_instance",
# not "main", so Dash's default relative-path resolution would look inside
# app/ rather than the project root. Explicit path fixes that.

from pathlib import Path

import dash

from app.index_string import INDEX_STRING
import app.plotly_template



_PROJECT_ROOT = Path(__file__).parent.parent

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="",
    assets_folder=str(_PROJECT_ROOT / "assets"),
    title="Artemis II • Mission Playback",
    update_title=None,
    index_string=INDEX_STRING,
)

server = app.server