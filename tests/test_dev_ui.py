import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dev_ui import install_dev_ui
from app.static_resources import install_static_resources


class TestDevUi(unittest.TestCase):
    def test_shared_help_is_served_for_both_plugins_and_custom_paths(self):
        resources = Path(__file__).resolve().parents[1] / "resources"
        with patch.dict(os.environ, {"RESOURCE_DIR": str(resources)}):
            app = FastAPI()
            install_static_resources(app, "/custom-python")
            install_static_resources(app, "/custom-cpp", "Cpp", root_alias=False)
        client = TestClient(app)
        for prefix in ("", "/custom-python", "/custom-cpp"):
            with self.subTest(prefix=prefix):
                response = client.get(f"{prefix}/static/help%2FEnvironment.html")
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])
                self.assertEqual(response.content, (resources / "help/Environment.html").read_bytes())
                self.assertEqual(client.get(f"{prefix}/static/help/missing.html").status_code, 404)
                self.assertEqual(client.get(f"{prefix}/static/help/%2e%2e/plugins/Python/PythonScript.js").status_code, 404)

    def test_bundled_ace_is_served_for_both_plugins_and_custom_paths(self):
        resources = Path(__file__).resolve().parents[1] / "resources"
        with patch.dict(os.environ, {"RESOURCE_DIR": str(resources)}):
            app = FastAPI()
            install_static_resources(app, "/custom-python")
            install_static_resources(app, "/custom-cpp", "Cpp", root_alias=False)
        client = TestClient(app)
        for prefix in ("", "/custom-python", "/custom-cpp"):
            for name in ("ace.js", "mode-python.js", "mode-c_cpp.js", "theme-monokai.js", "theme-chrome.js", "ext-searchbox.js"):
                with self.subTest(prefix=prefix, name=name):
                    response = client.get(f"{prefix}/static/ace/1.44.0/{name}")
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("javascript", response.headers["content-type"])
                    self.assertEqual(response.content, (resources / "vendor/ace/1.44.0" / name).read_bytes())
            self.assertEqual(client.get(f"{prefix}/static/ace/1.44.0/missing.js").status_code, 404)
            self.assertEqual(client.get(f"{prefix}/static/ace/%2e%2e/%2e%2e/plugins/Python/PythonScript.js").status_code, 404)

    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            app = FastAPI()
            install_dev_ui(app, "/pluginpython")
        client = TestClient(app)
        self.assertEqual(client.get("/pluginpython/dev/config").status_code, 404)
        self.assertEqual(client.get("/pluginpython/dev/student").status_code, 404)
        self.assertEqual(client.get("/pluginpython/dev/resources/test.js").status_code, 404)

    def test_student_previews_load_first_example_with_editable_student_script(self):
        from shared.cpp_examples import cpp_examples
        from shared.question_examples import QuestionConfigDtoExamples
        from shared.sql_examples import sql_example

        resources = Path(__file__).resolve().parents[1] / "resources"
        cases = (
            ("Python", QuestionConfigDtoExamples()[0].model_dump()),
            ("Cpp", cpp_examples("c")[0]),
            ("SQL", sql_example(0).model_dump()),
        )
        for plugin, expected in cases:
            with self.subTest(plugin=plugin), patch.dict(os.environ, {
                "RESOURCE_DIR": str(resources), "PLUGIN_DEV_UI": "true",
            }):
                app = FastAPI()
                prefix = f"/custom/{plugin.lower()}"
                install_dev_ui(app, prefix, plugin)
                client = TestClient(app)
                response = client.get(f"{prefix}/dev/student")
                self.assertEqual(response.status_code, 200)
                self.assertIn("Example 1", response.text)
                script = f"{prefix}/dev/resources/plugins/{plugin}/{plugin}Script.js"
                self.assertIn(f'src="{script}"', response.text)
                self.assertEqual(client.get(script).status_code, 200)
                match = re.search(rf'initPlugin{plugin}\(JSON.stringify\((.*)\), true\);', response.text)
                self.assertIsNotNone(match)
                dto = json.loads(match.group(1))
                self.assertEqual(dto["serviceBase"], prefix)
                self.assertEqual(json.loads(dto["jsonData"]), expected)
                self.assertIn(f'id="{dto["tagName"]}_div"', response.text)
                self.assertIn(f'class="{dto["tagName"]}_inp" value=""', response.text)

    def test_student_preview_escapes_example_code_in_inline_script(self):
        from shared.question_config import QuestionConfigDto

        resources = Path(__file__).resolve().parents[1] / "resources"
        source = '</script><script>alert("example")</script>\n# Grüße'
        with patch.dict(os.environ, {"RESOURCE_DIR": str(resources), "PLUGIN_DEV_UI": "true"}), \
                patch("shared.question_examples.QuestionConfigDtoExamples",
                      return_value=[QuestionConfigDto(indication=source)]):
            app = FastAPI()
            install_dev_ui(app, "/pluginpython")
            page = TestClient(app).get("/pluginpython/dev/student").text
        self.assertNotIn(source, page)
        dto = json.loads(re.search(r'initPluginPython\(JSON.stringify\((.*)\), true\);', page).group(1))
        self.assertEqual(json.loads(dto["jsonData"])["indication"], source)

    def test_enabled_serves_dialog_and_resources_without_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            resources = root / "resources"
            resources.mkdir()
            (resources / "test.js").write_text("// test resource", encoding="utf-8")
            plugin_resources = resources / "plugins/Python"
            plugin_resources.mkdir(parents=True)
            project_resources = Path(__file__).resolve().parents[1] / "resources/plugins/Python"
            for name in ("python-logo.png", "unittest-logo.png"):
                (plugin_resources / name).write_bytes((project_resources / name).read_bytes())
            (root / "secret.txt").write_text("outside resources", encoding="utf-8")
            with patch.dict(os.environ, {"PLUGIN_DEV_UI": "true", "RESOURCE_DIR": str(resources)}):
                app = FastAPI()
                install_static_resources(app, "/custom")
                install_dev_ui(app, "/custom")
            client = TestClient(app)
            page = client.get("/custom/dev/config")
            self.assertEqual(page.status_code, 200)
            self.assertIn('/custom/dev/resources/plugins/Python/PythonConfigScript.js', page.text)
            self.assertIn('"serviceBase": "/custom"', page.text)
            self.assertEqual(client.get("/custom/dev/resources/test.js").text, "// test resource")
            self.assertEqual(client.get("/custom/dev/resources/%2e%2e/secret.txt").status_code, 404)
            for name in ("python-logo.png", "unittest-logo.png"):
                response = client.get(f"/custom/static/{name}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "image/png")
                self.assertEqual(response.content, (plugin_resources / name).read_bytes())
            self.assertEqual(client.get("/custom/static/%2e%2e/test.js").status_code, 404)


if __name__ == "__main__":
    unittest.main()
