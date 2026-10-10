import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.main import app
from app import code_execution_endpoints


BASE_PATH = "/pluginpython"


class TestEndpoints(unittest.TestCase):
    def test_cpu_time_survives_question_config_serialization(self):
        import base64
        import json
        from app.main import encode_question_config_base64, _extract_cputime, PluginDto

        encoded = encode_question_config_base64('{"cpuTime": 12}')
        self.assertEqual(json.loads(base64.b64decode(encoded))["cpuTime"], 12)
        self.assertEqual(_extract_cputime(plugin_dto=PluginDto(jsonData=encoded)), 12)

    def test_cpu_time_defaults_and_invalid_values(self):
        from app.main import _extract_cputime

        for value in (None, "", "invalid", 0, -1):
            with self.subTest(value=value):
                self.assertEqual(code_execution_endpoints._cputime_from_question_config({"cpuTime": value}), 5)
        self.assertEqual(_extract_cputime('{"cpuTime": "9"}'), 9)
        self.assertEqual(_extract_cputime(''), 5)

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_get_ping_returns_plain_text(self):
        response = self.client.get(f"{BASE_PATH}/ping")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "pong")

    def test_detailed_help_is_served_separately_from_plugin_overview(self):
        from app.main import PluginPython

        resources = Path(__file__).resolve().parents[1] / "resources"
        detailed = (resources / "help/Python.html").read_text(encoding="utf-8")
        overview = (resources / "plugins/Python/Python.html").read_text(encoding="utf-8")
        with patch.dict(os.environ, {"RESOURCE_DIR": str(resources)}):
            for path in ("/help", f"{BASE_PATH}/help"):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.headers["content-type"].startswith("text/html"))
                self.assertEqual(response.text.replace("\r\n", "\n"), detailed)
            self.assertEqual(PluginPython("python", "").get_help(), overview.strip())
        self.assertIn("Linter presets", detailed)
        self.assertNotIn("Linter presets", overview)

    def test_help_files_are_served_with_and_without_proxy_prefix(self):
        from fastapi import FastAPI
        from app.static_resources import install_static_resources

        with tempfile.TemporaryDirectory() as directory:
            resources = Path(directory) / "plugins/Python"
            resources.mkdir(parents=True)
            examples = "<!doctype html><h1>Examples</h1>"
            helpers = "class RedirectedStdout: pass\n"
            (resources / "examples.html").write_text(examples, encoding="utf-8")
            (resources / "helpers.py").write_text(helpers, encoding="utf-8")
            (Path(directory) / "secret.txt").write_text("private", encoding="utf-8")
            with patch.dict(os.environ, {"RESOURCE_DIR": directory}):
                static_app = FastAPI()
                install_static_resources(static_app, BASE_PATH)
                client = TestClient(static_app)
                for prefix in ("", BASE_PATH):
                    with self.subTest(prefix=prefix):
                        response = client.get(f"{prefix}/static/examples.html")
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.text, examples)
                        self.assertTrue(response.headers["content-type"].startswith("text/html"))
                        response = client.get(f"{prefix}/static/helpers.py")
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.text.replace("\r\n", "\n"), helpers)
                        self.assertEqual(client.get(f"{prefix}/static/missing.html").status_code, 404)
                        self.assertEqual(client.get(f"{prefix}/static/%2E%2E/secret.txt").status_code, 404)

    def test_get_info_returns_service_info_dto(self):
        response = self.client.get(f"{BASE_PATH}/open/info")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["serviceName"], "PythonCppPlugin")
        self.assertEqual(body["author"], "Klaus Stocker")

    def test_post_configurationinfo_returns_configuration_dto_shape(self):
        payload = {
            "typ": "PIG",
            "name": "PluginVomTester",
            "config": "",
            "configurationID": "cfg-1",
            "timeout": 300,
        }

        response = self.client.post(f"{BASE_PATH}/open/configurationinfo", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["configurationID"], "cfg-1")
        self.assertEqual(body["configurationMode"], 0)
        self.assertTrue(body["useQuestion"])


    def test_loadplugindto_does_not_serialize_token(self):
        response = self.client.post(
            f"{BASE_PATH}/open/loadplugindto",
            json={"typ": "PIG", "name": "PluginVomTester", "config": ""},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("pluginToken", body.get("params") or {})

    def test_exectoken_returns_execution_token_for_script_startup(self):
        response = self.client.get(f"{BASE_PATH}/exectoken")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"token": code_execution_endpoints.get_exec_token()})

    def test_get_buildhash_returns_commit_hash(self):
        headers = {"Authorization": f"Bearer {code_execution_endpoints.get_exec_token()}"}
        original_env = os.environ.get("PLUGIN_BUILD_HASH")
        os.environ["PLUGIN_BUILD_HASH"] = "test-build-hash"
        try:
            response = self.client.get(f"{BASE_PATH}/buildhash", headers=headers)
        finally:
            if original_env is None:
                os.environ.pop("PLUGIN_BUILD_HASH", None)
            else:
                os.environ["PLUGIN_BUILD_HASH"] = original_env

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"commitHash": "test-build-hash"})

    def test_file_manager_upload_download_delete_uses_persistent_storage(self):
        headers = {"Authorization": f"Bearer {code_execution_endpoints.get_exec_token()}"}
        samples = [
            {
                "display_name": "original-notes.txt",
                "source_name": "original-notes.txt",
                "content": b"Hello from a small text file.\nSecond line.\n",
                "content_type": "text/plain",
            },
            {
                "display_name": "original-data.bin",
                "source_name": "original-data.bin",
                "content": bytes([0, 1, 2, 3, 250, 251, 252, 253, 254, 255]),
                "content_type": "application/octet-stream",
            },
        ]

        original_storage_root = code_execution_endpoints.FILE_STORAGE_ROOT
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_root = Path(temp_dir)
            code_execution_endpoints.FILE_STORAGE_ROOT = storage_root
            try:
                uploaded_files = []

                for sample in samples:
                    response = self.client.post(
                        f"{BASE_PATH}/files/upload",
                        headers=headers,
                        data={"name": "ignored-display-name.txt"},
                        files={
                            "file": (
                                sample["source_name"],
                                sample["content"],
                                sample["content_type"],
                            )
                        },
                    )

                    self.assertEqual(response.status_code, 200)
                    body = response.json()
                    self.assertEqual(body["displayName"], sample["source_name"])
                    self.assertEqual(body["size"], len(sample["content"]))
                    self.assertNotIn("contentType", body)
                    self.assertIn("storedName", body)

                    stored_path = storage_root / body["storedName"]
                    self.assertTrue(stored_path.is_file())
                    self.assertEqual(stored_path.read_bytes(), sample["content"])
                    uploaded_files.append((sample, body, stored_path))

                for sample, body, _stored_path in uploaded_files:
                    response = self.client.get(
                        f"{BASE_PATH}/files/download/{body['storedName']}",
                        headers=headers,
                        params={"name": sample["display_name"]},
                    )

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.content, sample["content"])

                _sample, file_to_delete, deleted_path = uploaded_files[0]
                response = self.client.post(
                    f"{BASE_PATH}/files/delete",
                    headers=headers,
                    json={"storedName": file_to_delete["storedName"]},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"deleted": True})
                self.assertFalse(deleted_path.exists())
                self.assertTrue(uploaded_files[1][2].is_file())
            finally:
                code_execution_endpoints.FILE_STORAGE_ROOT = original_storage_root

    def test_post_generalinfo_returns_matching_typ(self):
        response = self.client.post(f"{BASE_PATH}/open/generalinfo", json="PIG")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["typ"], "PIG")

    @patch("app.code_execution_endpoints.JobeWrapper")
    def test_run_uses_configured_cputime(self, jobe_wrapper_mock):
        jobe_wrapper_mock.createFiles.return_value = []
        headers = {"Authorization": f"Bearer {code_execution_endpoints.get_exec_token()}"}
        jobe_wrapper_mock.return_value.run_test.return_value = "run result"

        response = self.client.post(
            f"{BASE_PATH}/run",
            headers=headers,
            json={
                "code": "print(1)",
                "questionConfigDto": {"cpuTime": 12},
            },
        )

        self.assertEqual(response.status_code, 200)
        jobe_wrapper_mock.return_value.run_test.assert_called_once_with(
            "python3", "print(1)", "test.py", [], cputime=12)

    @patch("app.code_execution_endpoints.checkCode")
    def test_check_uses_configured_cputime(self, check_code_mock):
        headers = {"Authorization": f"Bearer {code_execution_endpoints.get_exec_token()}"}
        check_code_mock.return_value = "check result"

        response = self.client.post(
            f"{BASE_PATH}/check",
            headers=headers,
            json={
                "code": "def add(): return 3",
                "testcode": 'tests',
                "questionConfigDto": {"cpuTime": 12},
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(check_code_mock.call_args.kwargs["cputime"], 12)

    @patch("app.code_execution_endpoints.scoreCode")
    def test_score_plugin_accepts_comma_decimal_linter_weight(self, score_mock):
        headers = {"Authorization": f"Bearer {code_execution_endpoints.get_exec_token()}"}
        score_mock.return_value = (0.75, "score result")

        response = self.client.post(
            f"{BASE_PATH}/scorePlugin",
            headers=headers,
            json={
                "code": "print(1)",
                "testcode": "",
                "questionConfigDto": {
                    "linterConfig": "--disable=C0114",
                    "linterWeight": "1,5",
                    "cpuTime": "9",
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["score"], 0.75)
        score_mock.assert_called_once()
        self.assertEqual(score_mock.call_args.args[4], 1.5)
        self.assertEqual(score_mock.call_args.kwargs["cputime"], 9)


if __name__ == "__main__":
    unittest.main()
