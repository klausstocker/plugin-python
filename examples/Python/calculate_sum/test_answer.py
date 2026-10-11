import unittest

import answer  # pylint: disable=import-error


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_positive(self):
        self.assertEqual(answer.calculate_sum(2, 3), 5)

    def test_negative(self):
        self.assertEqual(answer.calculate_sum(-4, 1), -3)

    def test_zero(self):
        self.assertEqual(answer.calculate_sum(0, 0), 0)
