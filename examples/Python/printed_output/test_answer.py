import unittest
from helpers import RedirectedStdout  # pylint: disable=import-error


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_printed_output(self):
        with RedirectedStdout() as output:
            import answer  # pylint: disable=import-error,import-outside-toplevel,unused-import
        self.assertEqual(str(output), "hello world\n", "Print hello world followed by a newline.")
