import unittest
import sys
from pathlib import Path

# The plugin supplies helpers.py; this fallback supports repository-local tests.
_shared_dir = Path(__file__).resolve().parents[2] / "shared"
if (_shared_dir / "helpers.py").is_file():
    sys.path.insert(0, str(_shared_dir))

from helpers import RedirectedStdout

import answer


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_greeting(self):
        with RedirectedStdout() as output:
            answer.greet("Ada")
        self.assertEqual(str(output), "Hello, Ada!\n", "Include the greeting and a newline.")

    def test_another_name(self):
        with RedirectedStdout() as output:
            answer.greet("Lin")
        self.assertEqual(str(output), "Hello, Lin!\n")
