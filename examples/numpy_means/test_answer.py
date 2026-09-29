import unittest
import numpy as np

import answer


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def test_columns(self):
        result = answer.column_means(np.array([[1.0, 2.0], [3.0, 6.0]]))
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (2,))
        np.testing.assert_allclose(result, [2.0, 4.0])

    def test_single_row(self):
        result = answer.column_means(np.array([[1.5, -2.0, 0.0]]))
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.shape, (3,))
        np.testing.assert_allclose(result, [1.5, -2.0, 0.0])
