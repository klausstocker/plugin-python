"""Verify example submissions without requiring a running Jobe server."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from shared.check import checkCode
from shared.jobe_wrapper import JobeWrapper, RunResult
from shared.question_examples import QuestionConfigDtoExamples


class TestCalculateSumSubmission(unittest.TestCase):
    def test_helper_is_available_in_isolated_submission(self):
        example = QuestionConfigDtoExamples()[0]
        self.assertNotIn("helpers.py", example.files)
        validation = example.validation + '''
    def test_imported_helper_is_preserved(self):
        import helpers
        self.assertIs(RedirectedStdout, helpers.RedirectedStdout)
'''
        files = JobeWrapper.createFiles({
            name: content.encode("utf-8") for name, content in example.files.items()
        })

        def run_submission(language, code, filename, submitted_files):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for _file_id, name, content in submitted_files:
                    (root / name).write_bytes(content)
                (root / filename).write_text(code, encoding="utf-8")
                completed = subprocess.run(
                    [sys.executable, "-E", filename], cwd=root,
                    capture_output=True, text=True, timeout=15,
                )
                return RunResult({
                    "outcome": 15 if completed.returncode == 0 else 12,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                })

        with patch.object(JobeWrapper, "run_test", side_effect=run_submission):
            result = checkCode(
                "unused", example.indication, validation, files=files,
            )
        self.assertEqual(result.count, 3, repr(result))
        self.assertTrue(result.wasSuccessful(), repr(result))
