"""Verify example submissions without requiring a running Jobe server."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.dataset_helper import DatasetVariable, dataset_file_from_variables
from shared.check import checkCode
from shared.jobe_wrapper import JobeWrapper, RunResult
from shared.question_examples import (
    EXAMPLE_NAMES,
    REFERENCE_EXAMPLE_NAMES,
    QuestionConfigDtoExamples,
    QuestionConfigDtoExamplesWorkingIndication,
)


class TestExampleSubmissions(unittest.TestCase):
    def test_helper_is_available_in_isolated_submission(self):
        example = QuestionConfigDtoExamplesWorkingIndication()[0]
        self.assertNotIn("helpers.py", example.files)
        example.validation += '''
    def test_imported_helper_is_preserved(self):
        import helpers
        self.assertIs(RedirectedStdout, helpers.RedirectedStdout)
'''
        result = self.run_example(example, example.indication)
        self.assertEqual(result.count, 3, repr(result))
        self.assertTrue(result.wasSuccessful(), repr(result))

    def run_example(self, example, code, dataset_value=7):
        def run_submission(language, source, filename, submitted_files):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for _file_id, name, content in submitted_files:
                    (root / name).write_bytes(content)
                (root / filename).write_text(source, encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, "-E", filename], cwd=root,
                    capture_output=True, text=True, timeout=15,
                )
                return RunResult({
                    "outcome": 15 if completed.returncode == 0 else 12,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                })

        file_data = {
            name: content.encode("utf-8") for name, content in example.files.items()
        }
        file_data.update(dataset_file_from_variables([
            DatasetVariable(name="number", value=dataset_value),
        ]))
        files = JobeWrapper.createFiles(file_data)
        with patch.object(JobeWrapper, "run_test", side_effect=run_submission):
            return checkCode("unused", code, example.validation, files=files)

    def test_dataset_example_uses_current_value(self):
        index = EXAMPLE_NAMES.index("dataset_double")
        example = QuestionConfigDtoExamples()[index]
        # Test-only submission; the published example has no standalone solution.
        submission = "def double(value): return 2 * value"
        self.assertNotIn("dataset.py", example.files)
        self.assertEqual(example.datasetVariables, [])
        for value in (7, -3.5, 0):
            with self.subTest(value=value):
                result = self.run_example(example, submission, dataset_value=value)
                self.assertEqual(result.count, 2, repr(result))
                self.assertTrue(result.wasSuccessful(), repr(result))
        result = self.run_example(example, "def double(value): return 14", dataset_value=3)
        self.assertFalse(result.wasSuccessful(), repr(result))

    def test_all_reference_solutions_pass(self):
        examples = QuestionConfigDtoExamplesWorkingIndication()
        self.assertEqual(len(examples), len(REFERENCE_EXAMPLE_NAMES))
        for name, example in zip(REFERENCE_EXAMPLE_NAMES, examples):
            with self.subTest(example=name):
                result = self.run_example(example, example.indication)
                self.assertGreaterEqual(result.count, 2, repr(result))
                self.assertTrue(result.wasSuccessful(), repr(result))

    def test_student_templates_need_implementation(self):
        for name, example in zip(EXAMPLE_NAMES, QuestionConfigDtoExamples()):
            with self.subTest(example=name):
                result = self.run_example(example, example.indication)
                self.assertGreaterEqual(result.count, 2, repr(result))
                self.assertFalse(result.wasSuccessful(), repr(result))

    def test_html_guide_contains_solutions_and_matches_help_link(self):
        from html import unescape
        from scripts.build_examples_docs import build

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "examples.html"
            build(output)
            html = output.read_text(encoding="utf-8")
        root = Path(__file__).resolve().parents[1]
        for name in REFERENCE_EXAMPLE_NAMES:
            solution = (root / "examples" / name / "answer.py").read_text(encoding="utf-8")
            self.assertIn(solution.rstrip(), unescape(html))
        self.assertIn("def greet(name: str) -&gt; None:", html)
        self.assertIn("SELECT name FROM products WHERE price &lt; ?", html)
        self.assertIn("LeTTo dataset variable named <code>number</code> must exist", html)
        self.assertNotIn("dataset_double/answer.py", html)
        self.assertNotIn("Build the HTML guide", html)
        self.assertNotIn("Run locally", html)
        self.assertNotIn("Teacher checker", html)
        for filename in ("Python.html", "PythonConfigScript.js"):
            help_text = (root / "resources/plugins/Python" / filename).read_text(encoding="utf-8")
            self.assertIn('/images/plugins/Python/examples.html', help_text)
