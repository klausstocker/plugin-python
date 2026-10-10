# Required setup: Create dataset variables a and n in the LeTTo question yourself.
# Use integer values without units, with n >= 0 (for example, a = 3 and n = 4).
# Applying this example does not create them. Check/score use their current values.
# This test calculates b = a + n and passes the endpoints a and b to the student.

import unittest

import answer  # pylint: disable=import-error
import dataset  # pylint: disable=import-error
from helpers import RedirectedStdout  # pylint: disable=import-error


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_printed_numbers(self):
        a = int(dataset.a.value)
        b = a + int(dataset.n.value)
        with RedirectedStdout() as output:
            answer.print_numbers(a, b)
        expected = "".join(f"{number}\n" for number in range(a, b + 1))
        self.assertEqual(str(output), expected, "Print a through b, one integer per line.")
