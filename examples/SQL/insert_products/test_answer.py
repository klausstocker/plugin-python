import unittest
import answer


class Checker(unittest.TestCase):
    def setUp(self):
        answer.reset()

    def test_inserted_product(self):
        self.assertEqual(answer.connection.execute(
            'SELECT id, name, price FROM products ORDER BY id').fetchall(),
            [(1, 'Pen', 2), (2, 'Book', 8), (3, 'Ruler', 4)],
            'Insert Ruler and preserve the existing products')

    def test_returned_rows(self):
        self.assertEqual(answer.columns, ['id', 'name', 'price'])
        self.assertEqual(answer.rows, [(1, 'Pen', 2), (2, 'Book', 8), (3, 'Ruler', 4)],
                         'Return all products ordered by id')
