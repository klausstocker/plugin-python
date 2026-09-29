import unittest
import tempfile
from pathlib import Path

import answer


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_write_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "names.txt"
            answer.write_names(str(path), ["Ada", "Renée"])
            self.assertEqual(path.read_text(encoding="utf-8"), "Ada\nRenée\n")

    def test_replace_existing_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "names.txt"
            path.write_text("old content", encoding="utf-8")
            answer.write_names(str(path), [])
            self.assertEqual(path.read_text(encoding="utf-8"), "")
