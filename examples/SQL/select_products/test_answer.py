import unittest
import answer


class Checker(unittest.TestCase):
    def setUp(self):
        answer.reset()

    def test_result(self):
        self.assertEqual(answer.columns, ['name', 'price'])
        self.assertEqual(answer.rows, [('Pen', 2), ('Book', 8)], 'Return the products ordered by price')

    def test_database(self):
        self.assertEqual(answer.connection.execute(
            'SELECT name, price FROM products ORDER BY name').fetchall(),
            [('Book', 8), ('Pen', 2)], 'Keep the product data unchanged')
