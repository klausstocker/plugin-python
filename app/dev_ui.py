"""Opt-in standalone teacher/student previews and local resource serving."""

import json
import os
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


def install_dev_ui(app: FastAPI, service_path: str, plugin: str = "Python") -> None:
    if os.getenv("PLUGIN_DEV_UI", "false").lower() != "true":
        return

    prefix = f"{service_path}/dev"
    resources = Path(os.getenv("RESOURCE_DIR", "/app/resources"))
    app.mount(f"{prefix}/resources", StaticFiles(directory=resources), name=f"{plugin}-dev-resources")

    @app.get(f"{prefix}/student", response_class=HTMLResponse, include_in_schema=False)
    def student_preview() -> str:
        # Use the same first example as the corresponding configuration dialog.
        if plugin == "Cpp":
            from shared.cpp_examples import cpp_examples
            config = cpp_examples("c")[0]
        elif plugin == "SQL":
            from shared.sql_examples import sql_example
            config = sql_example(0).model_dump()
        else:
            from shared.question_examples import QuestionConfigDtoExamples
            config = QuestionConfigDtoExamples()[0].model_dump()
        dto = json.dumps({
            "tagName": "dev_student", "serviceBase": service_path,
            "jsonData": json.dumps(config),
        }).replace("<", "\\u003c")
        script_url = f"{prefix}/resources/plugins/{plugin}/{plugin}Script.js"
        return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{plugin} student preview — Example 1</title>
<script src="https://code.jquery.com/jquery-4.0.0.min.js"></script>
<script src="{escape(script_url, quote=True)}"></script>
</head>
<body>
<h1>{plugin} student preview — Example 1</h1>
<p>Edit the starter code and use the editor buttons. Reload this page to start a fresh preview.</p>
<input type="hidden" class="dev_student_inp" value="">
<div id="dev_student_div"></div>
<script>
initPlugin{plugin}(JSON.stringify({dto}), true);
</script>
</body></html>"""

    @app.get(f"{prefix}/config", response_class=HTMLResponse, include_in_schema=False)
    def configuration_dialog() -> str:
        script_url = f"{prefix}/resources/plugins/{plugin}/{plugin}ConfigScript.js"
        support_script = (f'<script src="{escape(prefix, quote=True)}/resources/plugins/SQL/SQLScript.js"></script>'
                          if plugin == 'SQL' else '')
        # JSON encoding also keeps custom service paths safe in the inline script.
        dto = json.dumps({"tagName": "dev", "serviceBase": service_path}).replace("<", "\\u003c")
        return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{plugin} plugin development dialog</title>
<script src="https://code.jquery.com/jquery-4.0.0.min.js"></script>
{support_script}
<script src="{escape(script_url, quote=True)}"></script>
</head>
<body>
<h1>{plugin} plugin development dialog</h1>
<input type="hidden" class="configform_config" value="{{}}">
<div id="configform_div"></div>
<script>
configPlugin{plugin}(JSON.stringify({dto}));
</script>
</body></html>"""
