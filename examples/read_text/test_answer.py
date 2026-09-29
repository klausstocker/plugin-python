import unittest
import tempfile
from pathlib import Path

import answer


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_supplied_file(self):
        self.assertEqual(answer.read_lines("names.txt"), ["Ada", "Renée", "Lin"])

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.txt"
            path.write_text("", encoding="utf-8")
            self.assertEqual(answer.read_lines(str(path)), [])
