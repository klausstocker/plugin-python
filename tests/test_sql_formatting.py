"""Exercise real formatter output and SQLite behavior through the format endpoint."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main, code_execution_endpoints as common
from shared.check_sql import sql_answer
from shared.formatting import format_source, FormatterUnavailable
from shared.sql_examples import EXAMPLE_NAMES, sql_example


class TestSqlFormatting(unittest.TestCase):
    def test_preserves_results_and_database_for_all_examples(self):
        for index, name in enumerate(EXAMPLE_NAMES):
            for solution in (False, True):
                with self.subTest(example=name, solution=solution):
                    example = sql_example(index, solution=solution)
                    formatted_sql = format_source(example.indication, 'sql')
                    formatted_preparation = format_source(example.preparation, 'sql')
                    self.assertEqual(format_source(formatted_sql, 'sql'), formatted_sql)
                    original, formatted = {}, {}
                    try:
                        exec(sql_answer(example.indication, example.preparation), original)
                        exec(sql_answer(formatted_sql, formatted_preparation), formatted)
                        self.assertEqual(formatted['results'], original['results'])
                        for table in ['products', 'categories'] if name == 'join_products' else ['products']:
                            for query in (f'PRAGMA table_info({table})', f'SELECT * FROM {table} ORDER BY rowid'):
                                self.assertEqual(formatted['connection'].execute(query).fetchall(),
                                                 original['connection'].execute(query).fetchall())
                    finally:
                        for answer in (original, formatted):
                            if 'connection' in answer:
                                answer['connection'].close()

    def test_preserves_comments_strings_and_trigger_bodies(self):
        code = """-- Keep this comment
create table messages(value text);
create trigger copy after insert on products begin
insert into messages values('select; -- Do Not Change');
end;
insert into products values('Ruler', 4);
select value from messages;
"""
        formatted = format_source(code, 'sql')
        self.assertIn('-- Keep this comment', formatted)
        self.assertIn("'select; -- Do Not Change'", formatted)
        answer = {}
        try:
            exec(sql_answer(formatted, sql_example(0).preparation), answer)
            self.assertEqual(answer['rows'], [('select; -- Do Not Change',)])
        finally:
            if 'connection' in answer:
                answer['connection'].close()

    def test_incomplete_sql_can_be_formatted_without_execution(self):
        self.assertIn('SELECT', format_source('select name from', 'sql'))

    def test_real_endpoint_formats_sql_and_python(self):
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        for filename, code, expected in [('main.sql', 'select 1;', 'SELECT 1;'),
                                          ('preparation.sql', 'create table t(n int);', 'CREATE TABLE'),
                                          ('main.py', 'x=1\n', 'x = 1')]:
            response = client.post('/pluginsql/format', headers=headers, json={'code': code, 'filename': filename})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIn(expected, response.json()['code'])

    def test_missing_sqlparse_does_not_return_replacement_code(self):
        with patch('shared.formatting.importlib.util.find_spec', return_value=None):
            with self.assertRaises(FormatterUnavailable):
                format_source('SELECT 1;', 'sql')
