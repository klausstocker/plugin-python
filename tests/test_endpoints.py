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
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_get_ping_returns_plain_text(self):
        response = self.client.get(f"{BASE_PATH}/ping")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "pong")

    def test_get_info_returns_service_info_dto(self):
        response = self.client.get(f"{BASE_PATH}/open/info")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["serviceName"], "pluginpython")
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

    def test_set_configuration_data_exposes_dataset_to_config_js(self):
        config_id = "cfg-dataset"
        self.client.post(
            f"{BASE_PATH}/open/configurationinfo",
            json={
                "typ": "PIG",
                "name": "DatasetPlugin",
                "config": "",
                "configurationID": config_id,
                "timeout": 300,
            },
        )

        response = self.client.post(
            f"{BASE_PATH}/open/setconfigurationdata",
            json={
                "typ": "PIG",
                "configurationID": config_id,
                "configuration": "",
                "questionDto": {
                    "id": 7,
                    "vars": {
                        "vars": {
                            "answer": {
                                "calcErgebnisDto": {"string": "42", "type": "NUMBER"},
                                "ze": "",
                            }
                        }
                    },
                    "cvars": {
                        "vars": {
                            "label": {
                                "calcErgebnisDto": {"string": "hello", "type": "STRING"}
                            }
                        }
                    },
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["params"]["dataset"]["vars"]["answer"]["calcErgebnisDto"]["string"], "42")
        self.assertEqual(body["params"]["dataset"]["cvars"]["label"]["calcErgebnisDto"]["string"], "hello")
        self.assertEqual(body["pluginDto"]["params"]["dataset"]["vars"]["answer"]["calcErgebnisDto"]["string"], "42")

    def test_dataset_payload_is_added_as_jobe_dataset_module(self):
        body = {
            "questionConfigDto": {
                "dataset": {
                    "vars": {
                        "answer": {"calcErgebnisDto": {"string": "42", "type": "NUMBER"}},
                        "items": {"calcErgebnisDto": {"json": "[1, 2, 3]", "type": "JSON"}},
                    },
                    "mvars": {
                        "computed": {"calcErgebnisDto": {"string": "true", "type": "BOOLEAN"}}
                    },
                }
            }
        }

        files = code_execution_endpoints._file_specs_from_body(body)

        self.assertIn("dataset.py", files)
        dataset_source = files["dataset.py"].decode("utf-8")
        self.assertIn("'answer': 42", dataset_source)
        self.assertIn("'items': [1, 2, 3]", dataset_source)
        self.assertIn("'computed': True", dataset_source)
        self.assertIn("globals().update(VARS)", dataset_source)

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
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["score"], 0.75)
        score_mock.assert_called_once()
        self.assertEqual(score_mock.call_args.args[4], 1.5)


if __name__ == "__main__":
    unittest.main()
