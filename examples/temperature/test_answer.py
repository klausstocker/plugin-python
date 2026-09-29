import unittest

import answer  # pylint: disable=import-error


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_freezing(self):
        self.assertAlmostEqual(answer.to_fahrenheit(0.0), 32.0)

    def test_fraction(self):
        self.assertAlmostEqual(answer.to_fahrenheit(37.1), 98.78)

    def test_negative(self):
        self.assertAlmostEqual(answer.to_fahrenheit(-40.0), -40.0)
