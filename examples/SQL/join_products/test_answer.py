import unittest
import answer


class Checker(unittest.TestCase):
    def setUp(self):
        answer.reset()

    def test_joined_rows(self):
        self.assertEqual(answer.columns, ['product', 'category'])
        self.assertEqual(answer.rows, [
            ('Notebook', 'Stationery'), ('Pen', 'Stationery'), ('SQL Guide', 'Books')],
            'Return each product with its category, ordered by product name')

    def test_database_unchanged(self):
        self.assertEqual(answer.connection.execute(
            'SELECT id, name, category_id FROM products ORDER BY id').fetchall(),
            [(1, 'Pen', 1), (2, 'Notebook', 1), (3, 'SQL Guide', 2)])
        self.assertEqual(answer.connection.execute(
            'SELECT id, name FROM categories ORDER BY id').fetchall(),
            [(1, 'Stationery'), (2, 'Books'), (3, 'Unused')])
