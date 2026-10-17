import unittest
import answer


class Checker(unittest.TestCase):
    def setUp(self):
        answer.reset()

    def test_returned_rows(self):
        self.assertEqual(answer.columns, ['name', 'price'])
        self.assertEqual(answer.rows, [('Book', 9), ('Pen', 3)], 'Return the updated prices ordered by name')

    def test_database_updated(self):
        self.assertEqual(answer.connection.execute('SELECT SUM(price) FROM products').fetchone(),
                         (12,), 'Update prices in the database')
