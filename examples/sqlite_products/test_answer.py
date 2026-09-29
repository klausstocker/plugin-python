import unittest
import sqlite3

import answer


class Checker(unittest.TestCase):  # Keep this name; test methods start with test_.
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        self.connection.execute("CREATE TABLE products (name TEXT, price REAL)")
        self.connection.executemany(
            "INSERT INTO products VALUES (?, ?)",
            [("Pencil", 1.5), ("Book", 8.0), ("Eraser", 1.0)],
        )

    def test_filtered_and_sorted(self):
        self.assertEqual(
            answer.affordable_products(self.connection, 2.0), ["Eraser", "Pencil"]
        )

    def test_strict_boundary(self):
        self.assertEqual(answer.affordable_products(self.connection, 1.5), ["Eraser"])

    def test_no_matches(self):
        self.assertEqual(answer.affordable_products(self.connection, 0.5), [])
