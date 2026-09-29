import unittest

import answer  # pylint: disable=import-error
from dataset import DATASET_VARIABLES  # pylint: disable=import-error


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_dataset_value(self):
        value = DATASET_VARIABLES["number"].value
        self.assertAlmostEqual(answer.double(value), 2 * value)

    def test_negated_dataset_value(self):
        value = -DATASET_VARIABLES["number"].value
        self.assertAlmostEqual(answer.double(value), 2 * value)
