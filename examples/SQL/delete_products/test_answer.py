import unittest
import answer


class Checker(unittest.TestCase):
    def setUp(self):
        answer.reset()

    def test_remaining_products(self):
        self.assertEqual(answer.connection.execute(
            'SELECT id, name, stock FROM products ORDER BY id').fetchall(),
            [(1, 'Pen', 5), (3, 'Ruler', 2)], 'Delete only the products with zero stock')

    def test_returned_rows(self):
        self.assertEqual(answer.columns, ['name', 'stock'])
        self.assertEqual(answer.rows, [('Pen', 5), ('Ruler', 2)],
                         'Return the remaining products ordered by name')
