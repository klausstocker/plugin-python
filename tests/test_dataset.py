import unittest

from app.dataset_helper import (
    DatasetVariable,
    dataset_file_from_variables,
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

    def test_dataset_file_from_variables_builds_jobe_upload_file(self):
        files = dataset_file_from_variables([
            DatasetVariable(name="myVar", value=42.0, unit="m1s-1")
        ])

        self.assertEqual(list(files.keys()), ["dataset.py"])
        self.assertIn(b"class DatasetVariable", files["dataset.py"])
        self.assertIn(b"myVar", files["dataset.py"])


if __name__ == "__main__":
    unittest.main()
