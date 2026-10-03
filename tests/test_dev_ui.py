import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.dev_ui import install_dev_ui


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
            (root / "secret.txt").write_text("outside resources", encoding="utf-8")
            with patch.dict(os.environ, {"PLUGIN_DEV_UI": "true", "RESOURCE_DIR": str(resources)}):
                app = FastAPI()
                install_dev_ui(app, "/custom")
            client = TestClient(app)
            page = client.get("/custom/dev/config")
            self.assertEqual(page.status_code, 200)
            self.assertIn('/custom/dev/resources/plugins/Python/PythonConfigScript.js', page.text)
            self.assertIn('"serviceBase": "/custom"', page.text)
            self.assertEqual(client.get("/custom/dev/resources/test.js").text, "// test resource")
            self.assertEqual(client.get("/custom/dev/resources/%2e%2e/secret.txt").status_code, 404)


if __name__ == "__main__":
    unittest.main()
