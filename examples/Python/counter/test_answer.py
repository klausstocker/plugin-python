import unittest

import answer  # pylint: disable=import-error


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_initial_value(self):
        counter = answer.Counter()
        self.assertEqual(counter.value(), 0)

    def test_increment(self):
        counter = answer.Counter()
        counter.increment()
        counter.increment()
        self.assertEqual(counter.value(), 2)

    def test_independent_instances(self):
        first = answer.Counter()
        second = answer.Counter()
        first.increment()
        self.assertEqual(second.value(), 0)
