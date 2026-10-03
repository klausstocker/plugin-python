import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dev_ui import install_dev_ui
from app.static_resources import install_static_resources


class TestDevUi(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=True):
            app = FastAPI()
            install_dev_ui(app, "/pluginpython")
        client = TestClient(app)
        self.assertEqual(client.get("/pluginpython/dev/config").status_code, 404)
        self.assertEqual(client.get("/pluginpython/dev/resources/test.js").status_code, 404)

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
