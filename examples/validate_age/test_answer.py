import unittest

import answer


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_valid(self):
        self.assertEqual(answer.validate_age(18), 18)

    def test_zero(self):
        self.assertEqual(answer.validate_age(0), 0)

    def test_negative(self):
        with self.assertRaises(ValueError):
            answer.validate_age(-1)
