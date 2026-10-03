"""Opt-in standalone configuration dialog and resource serving for local tests."""

import json
import os
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


def install_dev_ui(app: FastAPI, service_path: str) -> None:
    if os.getenv("PLUGIN_DEV_UI", "false").lower() != "true":
        return

    prefix = f"{service_path}/dev"
    resources = Path(os.getenv("RESOURCE_DIR", "/app/resources"))
    app.mount(f"{prefix}/resources", StaticFiles(directory=resources), name="dev-resources")

    @app.get(f"{prefix}/config", response_class=HTMLResponse, include_in_schema=False)
    def configuration_dialog() -> str:
        script_url = f"{prefix}/resources/plugins/Python/PythonConfigScript.js"
        # JSON encoding also keeps custom service paths safe in the inline script.
        dto = json.dumps({"tagName": "dev", "serviceBase": service_path}).replace("<", "\\u003c")
        return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Python plugin development dialog</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js"></script>
<script src="{escape(script_url, quote=True)}"></script>
</head>
<body>
<h1>Python plugin development dialog</h1>
<input type="hidden" class="configform_config" value="{{}}">
<div id="configform_div"></div>
<script>
configPluginPython(JSON.stringify({dto}));
// Resolve the dialog's existing Letto documentation link against dev resources.
const examplesLink = document.querySelector('#configPluginHelp a[href="/images/plugins/Python/examples.html"]');
if (examplesLink) examplesLink.href = {json.dumps(prefix + '/resources/plugins/Python/examples.html')};
</script>
</body></html>"""
