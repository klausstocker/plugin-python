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
        self.assertEqual(result.count, 2, repr(result))
        self.assertTrue(result.wasSuccessful(), repr(result))

    def test_printed_output_requires_exact_top_level_output(self):
        example = QuestionConfigDtoExamples()[EXAMPLE_NAMES.index("printed_output")]
        for code in (
            'print("Hello world")',
            'print("hello world", end="")',
            'print("hello world"); print("extra")',
            'def greet(): print("hello world")',
        ):
            with self.subTest(code=code):
                result = self.run_example(example, code)
                self.assertEqual(result.count, 1, repr(result))
                self.assertFalse(result.wasSuccessful(), repr(result))

    def run_example(self, example, code, dataset_values=None):
        def run_submission(language, source, filename, submitted_files, cputime=None):
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
        if dataset_values is None:
            dataset_values = {"a": 3, "n": 4}
        file_data.update(dataset_file_from_variables([
            DatasetVariable(name=name, value=value)
            for name, value in dataset_values.items()
        ]))
        files = JobeWrapper.createFiles(file_data)
        with patch.object(JobeWrapper, "run_test", side_effect=run_submission):
            return checkCode("unused", code, example.validation, files=files)

    def test_dataset_numbers_uses_current_values_and_exact_output(self):
        example = QuestionConfigDtoExamples()[EXAMPLE_NAMES.index("dataset_numbers")]
        root = Path(__file__).resolve().parents[1]
        solution = (root / "examples/Python/dataset_numbers/answer.py").read_text(encoding="utf-8")
        self.assertNotIn("dataset.py", example.files)
        self.assertEqual(example.datasetVariables, [])
        for a, n in ((3, 4), (-3, 2), (7, 0), (0, 100)):
            with self.subTest(a=a, n=n):
                result = self.run_example(example, solution, {"a": a, "n": n})
                self.assertEqual(result.count, 1, repr(result))
                self.assertTrue(result.wasSuccessful(), repr(result))
        for submission in (
            "def print_numbers(a, b):\n    for value in range(a, b): print(value)",
            'def print_numbers(a, b): print("3\\n4\\n5\\n6\\n7")',
            'def print_numbers(a, b):\n    for value in range(a, b + 1): print(value, end=" ")',
            'def print_numbers(a, b):\n    for value in range(a, b + 1): print(value)\n    print("extra")',
            "def print_numbers(a, n):\n    for value in range(a, a + n + 1): print(value)",
        ):
            with self.subTest(submission=submission):
                result = self.run_example(example, submission, {"a": -3, "n": 2})
                self.assertEqual(result.count, 1, repr(result))
                self.assertFalse(result.wasSuccessful(), repr(result))
                self.assertEqual(result.score(), 0, repr(result))

    def test_all_reference_solutions_pass(self):
        examples = QuestionConfigDtoExamplesWorkingIndication()
        self.assertEqual(len(examples), len(REFERENCE_EXAMPLE_NAMES))
        for name, example in zip(REFERENCE_EXAMPLE_NAMES, examples):
            with self.subTest(example=name):
                result = self.run_example(example, example.indication)
                self.assertGreaterEqual(result.count, 1 if name in {"printed_output", "dataset_numbers"} else 2, repr(result))
                self.assertTrue(result.wasSuccessful(), repr(result))

    def test_student_templates_need_implementation(self):
        for name, example in zip(EXAMPLE_NAMES, QuestionConfigDtoExamples()):
            with self.subTest(example=name):
                result = self.run_example(example, example.indication)
                self.assertGreaterEqual(result.count, 1 if name in {"printed_output", "dataset_numbers"} else 2, repr(result))
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
            solution = (root / "examples" / "Python" / name / "answer.py").read_text(encoding="utf-8")
            self.assertIn(solution.rstrip(), unescape(html))
        self.assertIn('print("hello world")', unescape(html))
        self.assertIn("SELECT name FROM products WHERE price &lt; ?", html)
        self.assertIn("LeTTo dataset variables named <code>a</code> and <code>n</code>", html)
        self.assertIn("dataset.a.value", html)
        self.assertIn("dataset.n.value", html)
        self.assertNotIn("dataset_double", html)
        self.assertNotIn("Celsius", html)
        self.assertNotIn("Build the HTML guide", html)
        self.assertNotIn("Run locally", html)
        self.assertNotIn("Teacher checker", html)
        help_text = (root / "resources/help/Python.html").read_text(encoding="utf-8")
        self.assertIn('href="static/examples.html"', help_text)
        self.assertIn('data-plugin-help-file="examples.html"', help_text)
