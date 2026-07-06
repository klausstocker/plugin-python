"""Unit tests for the calculate_sum example.

Run from this directory with:
    python -m unittest test_answer.py

Or run from the repository root with:
    python -m unittest discover -s examples/calculate_sum -p "test_*.py"
"""

import sys
import unittest
from io import StringIO

import answer


class RedirectedStdout:
    """Capture stdout so examples can test printed output with unittest."""

    def __init__(self):
        self._stdout = None
        self._string_io = None

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._string_io = StringIO()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._stdout

    def __str__(self):
        return self._string_io.getvalue()


def correct_implementation(arg1, arg2):
    """Expected behavior for calculate_sum."""
    total = arg1 + arg2
    print(f"the sum is {total}")
    return total


class Checker(unittest.TestCase):  # do not rename; plugin checks expect this name
    def test_return(self):  # test method names must start with 'test_'
        args = (1, 2)
        student_result = answer.calculate_sum(*args)
        expected_result = correct_implementation(*args)
        self.assertEqual(student_result, expected_result)

    def test_output(self):
        args = (3, 4)
        with RedirectedStdout() as student_out:
            answer.calculate_sum(*args)
        with RedirectedStdout() as expected_out:
            correct_implementation(*args)
        # messages in asserts are shown as feedback
        self.assertEqual(str(student_out), str(expected_out), "think about print")
