import unittest

import answer  # pylint: disable=import-error
import dataset # pylint: disable=import-error

class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_dataset_value(self):
        value = dataset.number.value
        self.assertAlmostEqual(answer.double(value), 2 * value)

    def test_negated_dataset_value(self):
        value = -dataset.number.value
        self.assertAlmostEqual(answer.double(value), 2 * value)
