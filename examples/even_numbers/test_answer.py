import unittest

import answer


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_mixed(self):
        self.assertEqual(answer.even_numbers([3, 2, -4, 2, 0]), [2, -4, 2, 0])

    def test_empty(self):
        self.assertEqual(answer.even_numbers([]), [])

    def test_no_matches(self):
        self.assertEqual(answer.even_numbers([1, 3]), [])
