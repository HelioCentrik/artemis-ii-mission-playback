# main.py
#
# Application entrypoint — thin shell only.
# App instance lives in app/dash_instance.py.
# All layout, callbacks, and playback architecture live in pages/playback.py.

import os
import logging

import dash

from app.dash_instance import app, server  # noqa: F401 — server exposed for Gunicorn

import pages.home      # noqa: F401 — registers route at /
import pages.playback  # noqa: F401 — registers route at /playback/



logging.getLogger("werkzeug").setLevel(logging.ERROR)

app.layout = dash.page_container

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8050)),
        debug=os.environ.get("DASH_DEBUG", "false").lower() == "true",
        threaded=False,
    )