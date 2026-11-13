import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from app.dataset_helper import (
    DatasetVariable,
    dataset_file_from_payload,
    dataset_file_from_variables,
    dataset_variables_from_payload,
    dataset_variables_to_python_source,
    extract_dataset_variables,
    extract_question_dataset_variables,
)


class TestDatasetVariableExtraction(unittest.TestCase):
    def test_extracts_name_value_and_unit_from_calc_json(self):
        var_hash = {
            "vars": {
                "myVar": {
                    "calcErgebnisDto": {
                        "type": "CALCULATE",
                        "string": "42'm1s-1'",
                        "json": (
                            "{\"type\":\"at.letto.math.calculate.CalcDoubleEinheit\","
                            "\"d\":42.0,"
                            "\"originalEinheitString\":\"\\u0027m1s-1\\u0027\"}"
                        ),
                    },
                    "ze": "m/s,10",
                }
            }
        }

        self.assertEqual(
            extract_dataset_variables(var_hash),
            [DatasetVariable(name="myVar", value=42.0, unit="m1s-1")],
        )

    def test_falls_back_to_calc_string_for_unit_when_json_is_missing(self):
        var_hash = {
            "myVar": {
                "calcErgebnisDto": {
                    "type": "CALCULATE",
                    "string": "42'm1s-1'",
                }
            }
        }

        self.assertEqual(
            extract_dataset_variables(var_hash),
            [DatasetVariable(name="myVar", value=42.0, unit="m1s-1")],
        )

    def test_numeric_ze_is_not_a_unit(self):
        var_hash = {
            "i": {
                "calcErgebnisDto": {"json": '{"d":1}', "string": "1"},
                "ze": "10",
            }
        }
        self.assertEqual(
            extract_dataset_variables(var_hash),
            [DatasetVariable(name="i", value=1, unit="")],
        )
        namespace = {}
        exec(dataset_variables_to_python_source(extract_dataset_variables(var_hash)), namespace)
        self.assertEqual(namespace["i"].unit, "")
        var_hash["i"]["ze"] = "m/s,10"
        self.assertEqual(
            extract_dataset_variables(var_hash),
            [DatasetVariable(name="i", value=1, unit="m/s")],
        )

    def test_existing_unit_string_is_passed_through(self):
        for unit in ("", "10", "m/s"):
            self.assertEqual(
                dataset_variables_from_payload([{"name": "i", "value": 1, "unit": unit}]),
                [DatasetVariable(name="i", value=1, unit=unit)],
            )

    def test_extracts_from_question_primary_vars_only(self):
        question = {
            "vars": {
                "vars": {
                    "myVar": {
                        "calcErgebnisDto": {
                            "json": "{\"d\":42.0,\"originalEinheitString\":\"\\u0027m1s-1\\u0027\"}"
                        }
                    }
                }
            },
            "cvars": {"vars": {"pi": {"calcErgebnisDto": {"json": "{\"d\":3.14}"}}}},
        }

        self.assertEqual(
            extract_question_dataset_variables(question),
            [DatasetVariable(name="myVar", value=42.0, unit="m1s-1")],
        )

    def test_renders_dataset_variables_as_importable_python_module(self):
        source = dataset_variables_to_python_source([
            DatasetVariable(name="myVar", value=42.0, unit="m1s-1")
        ])
        namespace = {}

        exec(source, namespace)

        self.assertEqual(namespace["myVar"].value, 42.0)
        self.assertEqual(namespace["myVar"].unit, "m1s-1")
        self.assertEqual(namespace["DATASET_VARIABLES"]["myVar"].value, 42.0)
        self.assertEqual(namespace["DATASET_VARIABLES"]["myVar"].unit, "m1s-1")

    def test_normalizes_extracted_dataset_variable_payload(self):
        payload = {
            "datasetVariables": [
                {"name": "myVar", "value": 42.0, "unit": "m1s-1"}
            ]
        }

        self.assertEqual(
            dataset_variables_from_payload(payload),
            [DatasetVariable(name="myVar", value=42.0, unit="m1s-1")],
        )
        self.assertEqual(list(dataset_file_from_payload(payload).keys()), ["dataset.py"])
        self.assertEqual(
            dataset_variables_from_payload(
                '[{"name":"myVar","value":42.0,"unit":"m1s-1"}]'
            ),
            [DatasetVariable(name="myVar", value=42.0, unit="m1s-1")],
        )

    def test_dataset_file_from_variables_builds_jobe_upload_file(self):
        files = dataset_file_from_variables([
            DatasetVariable(name="myVar", value=42.0, unit="m1s-1")
        ])

        self.assertEqual(list(files.keys()), ["dataset.py"])
        self.assertIn(b"class DatasetVariable", files["dataset.py"])
        self.assertIn(b"myVar", files["dataset.py"])

    def test_empty_dataset_source_has_no_variables(self):
        namespace = {}

        exec(dataset_variables_to_python_source([]), namespace)

        self.assertEqual(namespace["DATASET_VARIABLES"], {})
        self.assertNotIn("_dataset_variable", namespace)
        self.assertNotIn("_dataset_value", namespace)

    def test_importing_dataset_without_variables_succeeds(self):
        for payload in (None, {}, {"datasetVariables": []}, {"datasetVariables": None}):
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as directory:
                files = dataset_file_from_payload(payload)
                self.assertEqual(set(files), {"dataset.py"})
                (Path(directory) / "dataset.py").write_bytes(files["dataset.py"])
                result = subprocess.run(
                    [sys.executable, "-c", (
                        "import dataset\n"
                        "from dataset import DATASET_VARIABLES\n"
                        "assert DATASET_VARIABLES == {}\n"
                        "try:\n"
                        "    from dataset import missing_variable\n"
                        "except ImportError:\n"
                        "    pass\n"
                        "else:\n"
                        "    raise AssertionError('Missing variable was importable')\n"
                    )],
                    cwd=directory, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
