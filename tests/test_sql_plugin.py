import base64
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import main, sql_execution_endpoints as sql_api, code_execution_endpoints as common
from app.dev_ui import install_dev_ui
from app.static_resources import install_static_resources
from shared.check_result import CheckResult
from shared.check_sql import check_sql, sql_answer
from shared.sql_examples import EXAMPLE_NAMES, sql_example


ROOT = Path(__file__).resolve().parents[1]
PREPARATION = 'CREATE TABLE items (value INTEGER); INSERT INTO items VALUES (1), (2);'
TESTS = '''import unittest
import answer
class Checker(unittest.TestCase):
    def test_rows(self):
        self.assertEqual(answer.rows, [(3,), (4,)])
    def test_database(self):
        self.assertEqual(answer.connection.execute('SELECT SUM(value) FROM items').fetchone(), (7,))
'''


def local_jobe_run(_self, language, source, filename, files=None, **kwargs):
    """Execute exactly the runner and uploaded files that would be sent to Jobe."""
    from shared.jobe_wrapper import RunResult
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for _, name, content in files or []:
            (root / name).write_bytes(content)
        (root / filename).write_text(source, encoding='utf-8')
        process = subprocess.run([sys.executable, filename], cwd=directory,
                                 capture_output=True, text=True, timeout=10)
        return RunResult({'outcome': 15 if process.returncode == 0 else 20,
                           'stdout': process.stdout, 'stderr': process.stderr, 'cmpinfo': ''})


class TestSqlRuntime(unittest.TestCase):
    def answer(self, code, preparation=PREPARATION):
        namespace = {}
        exec(sql_answer(code, preparation), namespace)
        self.addCleanup(namespace['connection'].close)
        return namespace

    def test_results_and_database_mutations(self):
        answer = self.answer('UPDATE items SET value=value+2; SELECT value FROM items ORDER BY value; SELECT COUNT(*) AS total FROM items;')
        self.assertEqual(answer['results'], [
            {'columns': ['value'], 'rows': [(3,), (4,)]},
            {'columns': ['total'], 'rows': [(2,)]}])
        self.assertEqual(answer['connection'].execute('SELECT SUM(value) FROM items').fetchone(), (7,))
        self.assertEqual(answer['rows'], [(2,)])

    def test_semicolons_comments_triggers_and_final_statement(self):
        answer = self.answer("""CREATE TABLE log (message TEXT);
CREATE TRIGGER changed AFTER INSERT ON items BEGIN
INSERT INTO log VALUES ('a;b');
INSERT INTO log VALUES ('c');
END;
INSERT INTO items VALUES (3); -- ignored ;
SELECT message FROM log; SELECT 'last;value' AS quoted -- no final semicolon
""")
        self.assertEqual(answer['results'][0]['rows'], [('a;b',), ('c',)])
        self.assertEqual(answer['rows'], [('last;value',)])

    def test_sql_preparation_and_reset(self):
        answer = self.answer('UPDATE items SET value=value+1 RETURNING value;')
        self.assertEqual(answer['rows'], [(2,), (3,)])
        answer['connection'].execute('DELETE FROM items')
        answer['reset']()
        self.assertEqual(answer['connection'].execute('SELECT value FROM items').fetchall(), [(2,), (3,)])
        answer['connection'].close()

    def test_empty_and_non_query_input(self):
        for code in ('', '-- comment only', 'UPDATE items SET value=7; -- trailing comment'):
            with self.subTest(code=code):
                answer = self.answer(code)
                self.assertEqual(answer['results'], [])
                self.assertEqual(answer['columns'], [])

    def test_invalid_sql_python_injection_and_attach_fail(self):
        for code in ('SELECT missing FROM items;', "';\nraise RuntimeError('injected')\n#", "ATTACH DATABASE ':memory:' AS other;"):
            with self.subTest(code=code), self.assertRaises(sqlite3.Error):
                self.answer(code)

    @patch('shared.jobe_wrapper.JobeWrapper.run_test', local_jobe_run)
    def test_real_generated_runner_scores_full_partial_and_zero(self):
        for code, score in [('UPDATE items SET value=value+2; SELECT value FROM items ORDER BY value;', 1),
                            ('UPDATE items SET value=value+2; SELECT 99;', .5), ('SELECT value FROM items;', 0),
                            ('SELECT missing FROM items;', 0)]:
            with self.subTest(code=code):
                result = check_sql('unused', code, TESTS, PREPARATION)
                self.assertEqual(result.score(), score, repr(result))

    @patch('shared.jobe_wrapper.JobeWrapper.run_test', local_jobe_run)
    def test_example_starter_and_solution(self):
        for index, name in enumerate(EXAMPLE_NAMES):
            for solution in (False, True):
                with self.subTest(example=name, solution=solution):
                    entry = sql_example(index, solution=solution)
                    result = check_sql('unused', entry.indication, entry.validation, entry.preparation)
                    expected = 1 if solution or index == 0 else .5 if name == 'join_products' else 0
                    self.assertEqual(result.score(), expected, repr(result))

    @patch('shared.jobe_wrapper.JobeWrapper.run_test', local_jobe_run)
    def test_execution_happens_even_when_teacher_does_not_import_answer(self):
        result = check_sql('unused', 'invalid sql;', 'import unittest\nclass Checker(unittest.TestCase):\n    def test_true(self): self.assertTrue(True)')
        self.assertEqual(result.score(), 0)

    def test_python_preparation_is_rejected(self):
        client = TestClient(main.app)
        response = client.post('/pluginsql/run', headers={'Authorization': 'Bearer ' + common.get_exec_token()}, json={
            'code': 'SELECT value FROM items;', 'questionConfigDto': {
                'preparationLanguage': 'python',
                'preparation': "import dataset\nconnection.execute('CREATE TABLE items (value INTEGER)')\nconnection.execute('INSERT INTO items VALUES (?)', (dataset.n.value,))",
                'datasetVariables': [{'name': 'n', 'value': 17}]}})
        self.assertEqual(response.status_code, 400, response.text)

    @patch('shared.jobe_wrapper.JobeWrapper.run_test', local_jobe_run)
    def test_future_import_in_teacher_tests(self):
        result = check_sql('unused', 'SELECT 1;', 'from __future__ import annotations\nimport unittest\nclass Checker(unittest.TestCase):\n    def test_rows(self): self.assertEqual(answer.rows, [(1,)])')
        self.assertEqual(result.score(), 1, repr(result))


class TestSqlPlugin(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.headers = {'Authorization': 'Bearer ' + common.get_exec_token()}

    def test_registry_and_configuration_roundtrip(self):
        self.assertEqual(set(self.client.get('/open/pluginlist').json()), {'Python', 'Cpp', 'SQL'})
        config = {'preparation': PREPARATION, 'preparationLanguage': 'sql', 'cpuTime': 9,
                  'validation': TESTS, 'indication': 'SELECT 1;', 'linterWeight': 1}
        for endpoint in ('/open/loadplugindto', '/open/reloadplugindto', '/pluginpython/api/open/reloadplugindto'):
            response = self.client.post(endpoint, json={'typ': 'SQL', 'name': 'q', 'config': json.dumps(config)})
            self.assertEqual(response.status_code, 200, response.text)
            dto = response.json()
            self.assertEqual(dto['params']['serviceBase'], '/pluginsql')
            saved = json.loads(base64.b64decode(dto['jsonData']))
            self.assertEqual(saved['preparation'], PREPARATION)
            self.assertEqual(saved['preparationLanguage'], 'sql')
            self.assertEqual(saved['cpuTime'], 9)
            self.assertNotIn('linterWeight', saved)

    def test_authentication_and_bad_requests(self):
        for endpoint in ('run', 'check', 'scorePlugin', 'example'):
            self.assertEqual(self.client.post('/pluginsql/' + endpoint, json={'code': ''}).status_code, 401)
        for body in ([], {}, {'code': 'SELECT 1', 'questionConfigDto': {'cpuTime': 0}},
                     {'code': '', 'questionConfigDto': {'preparationLanguage': 'javascript'}}):
            self.assertEqual(self.client.post('/pluginsql/run', headers=self.headers, json=body).status_code, 400)
        response = self.client.post('/pluginsql/check', headers=self.headers, json={'code': 'SELECT 1'})
        self.assertEqual(response.status_code, 400)

    def test_example_api_loads_all_five_and_rejects_invalid_indices(self):
        self.assertEqual(len(EXAMPLE_NAMES), 5)
        for index, name in enumerate(EXAMPLE_NAMES):
            response = self.client.post('/pluginsql/example', headers=self.headers, json={'index': index})
            self.assertEqual(response.status_code, 200, response.text)
            data = response.json()
            self.assertEqual(data['names'], list(EXAMPLE_NAMES))
            self.assertEqual(data['count'], 5)
            folder = ROOT / 'examples/SQL' / name
            self.assertEqual(data['output']['indication'], (folder / 'template.sql').read_text())
            self.assertEqual(data['output']['preparation'], (folder / 'preparation.sql').read_text())
            self.assertEqual(data['output']['validation'], (folder / 'test_answer.py').read_text())
            self.assertNotIn('solution', data['output'])
        for body in ([], {'index': -1}, {'index': 5}, {'index': True}, {'index': '1'}, {'index': None}):
            response = self.client.post('/pluginsql/example', headers=self.headers, json=body)
            self.assertEqual(response.status_code, 400, response.text)

    @patch('shared.jobe_wrapper.JobeWrapper.run_test', local_jobe_run)
    def test_run_and_teacher_grading_use_real_runner(self):
        body = {'code': 'UPDATE items SET value=value+2; SELECT value FROM items ORDER BY value;',
                'questionConfigDto': {'preparation': PREPARATION, 'validation': TESTS}}
        run = self.client.post('/pluginsql/run', headers=self.headers, json=body)
        self.assertEqual(run.status_code, 200, run.text)
        self.assertTrue(run.json()['success'], run.text)
        self.assertIn('(3,)', run.json()['output'])
        for endpoint in ('check', 'scorePlugin'):
            response = self.client.post('/pluginsql/' + endpoint, headers=self.headers, json=body)
            self.assertEqual(response.json()['score'], 1, response.text)
            self.assertGreaterEqual(response.json()['elapsedSeconds'], 0)

    @patch('shared.jobe_wrapper.JobeWrapper.run_test', local_jobe_run)
    def test_dataset_variables_are_importable_in_sql_unit_tests(self):
        tests = '''import unittest
import answer
from dataset import n, DATASET_VARIABLES
class Checker(unittest.TestCase):
    def test_dataset_and_rows(self):
        self.assertEqual(n.value, 3)
        self.assertEqual(n.unit, 'm')
        self.assertEqual(DATASET_VARIABLES['target-count'].value, 2)
        self.assertEqual(answer.rows, [(n.value,)])
'''
        config = {'validation': tests, 'datasetVariables': [
            {'name': 'n', 'value': 3, 'unit': 'm'}, {'name': 'target-count', 'value': 2, 'unit': ''}]}
        for endpoint in ('check', 'scorePlugin'):
            response = self.client.post('/pluginsql/' + endpoint, headers=self.headers,
                                        json={'code': 'SELECT 3;', 'questionConfigDto': config})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['score'], 1, response.text)

    @patch('shared.jobe_wrapper.JobeWrapper.run_test', local_jobe_run)
    def test_lettoscore_uses_current_dataset_instead_of_saved_values(self):
        tests = '''import unittest
from dataset import n
class Checker(unittest.TestCase):
    def test_current_value(self):
        self.assertEqual(n.value, 7)
        self.assertEqual(n.unit, 'm')
'''
        config = {'validation': tests, 'datasetVariables': [{'name': 'n', 'value': 3, 'unit': 'old'}]}
        response = self.client.post('/open/score', json={
            'typ': 'SQL', 'config': json.dumps(config), 'antwort': 'SELECT 7;', 'grade': 8,
            'varsQuestion': {'vars': {'n': {'calcErgebnisDto': {'string': "7 'm'", 'json': json.dumps({'d': 7, 'originalEinheitString': 'm'})}}}}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['punkteIst'], 8, response.text)

    @patch('app.main.check_sql', return_value=CheckResult({'count': 2, 'failure_count': 1}))
    def test_lettoscore_uses_sql_settings_and_ignores_linter(self, check):
        config = {'preparation': PREPARATION, 'validation': TESTS, 'cpuTime': 9, 'linterWeight': 1}
        response = self.client.post('/open/score', json={'typ': 'SQL', 'config': json.dumps(config), 'antwort': 'SELECT 1;', 'grade': 8})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['punkteIst'], 4)
        self.assertEqual(check.call_args.args[3], PREPARATION)
        self.assertEqual(check.call_args.kwargs['cputime'], 9)

    def test_static_help_config_state_and_development_dialog(self):
        with patch.dict(os.environ, {'RESOURCE_DIR': str(ROOT / 'resources'), 'PLUGIN_DEV_UI': 'true'}):
            plugin = main.create_plugin('SQL', '', '')
            info = plugin.plugin_general_info('SQL')
            self.assertEqual(info.initPluginJS, 'initPluginSQL')
            self.assertTrue(all(lib.js_code for lib in info.javascriptLibrariesLocal))
            state = main.create_or_update_configuration_state('sql-test', typ='SQL', plugin_python=plugin)
            self.addCleanup(main.CONFIG_STATES.pop, 'sql-test', None)
            self.assertEqual(state.pluginConfigurationInfoDto.javaScriptMethode, 'configPluginSQL')
            self.assertIn('SQL - Plugin', state.pluginConfigDto.params['help'])
            app = FastAPI()
            install_static_resources(app, '/custom/sql', 'SQL', root_alias=False)
            install_dev_ui(app, '/custom/sql', 'SQL')
            client = TestClient(app)
            self.assertEqual(client.get('/custom/sql/static/SQLScript.js').status_code, 200)
            text = client.get('/custom/sql/dev/config').text
            self.assertIn('SQLScript.js', text)
            self.assertIn('SQLConfigScript.js', text)
            self.assertIn('SQL - Plugin', self.client.get('/pluginsql/help').text)


@unittest.skipUnless(os.getenv('SQL_JOBE_SERVER'), 'Set SQL_JOBE_SERVER to run against Jobe')
class TestSqlJobeIntegration(unittest.TestCase):
    def test_all_examples_grade_in_jobe(self):
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        with patch.dict(os.environ, {'JOBE_SERVER': os.environ['SQL_JOBE_SERVER']}):
            for index, name in enumerate(EXAMPLE_NAMES):
                for solution in (False, True):
                    with self.subTest(example=name, solution=solution):
                        entry = sql_example(index, solution=solution)
                        endpoint = 'scorePlugin' if solution else 'check'
                        response = client.post('/pluginsql/' + endpoint, headers=headers,
                                               json={'code': entry.indication, 'questionConfigDto': entry.model_dump()})
                        self.assertEqual(response.status_code, 200, response.text)
                        expected = 1 if solution or index == 0 else .5 if name == 'join_products' else 0
                        self.assertEqual(response.json()['score'], expected, response.text)
                        self.assertGreater(response.json()['elapsedSeconds'], 0)


if __name__ == '__main__':
    unittest.main()
