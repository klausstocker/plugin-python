import base64
import json
import os
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import main, cpp_execution_endpoints as cpp, code_execution_endpoints as common
from app.static_resources import install_static_resources
from app.dev_ui import install_dev_ui
from shared.check_result import CheckResult
from shared.cpp_examples import EXAMPLE_NAMES, cpp_examples

RESOURCES = Path(__file__).resolve().parents[1] / 'resources'


class TestCppPlugin(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.headers = {'Authorization': 'Bearer ' + common.get_exec_token()}

    def test_registry_keeps_python_and_adds_cpp(self):
        with patch.dict(os.environ, {'RESOURCE_DIR': str(RESOURCES)}):
            for typ, callback in [('Python', 'initPluginPython'), ('Cpp', 'initPluginCpp')]:
                plugin = main.create_plugin(typ, '', '')
                info = plugin.plugin_general_info(typ)
                self.assertEqual(info.initPluginJS, callback)
                self.assertEqual(len(info.javascriptLibrariesLocal), 2)
                self.assertTrue(all(lib.js_code for lib in info.javascriptLibrariesLocal))
            self.assertEqual(main.create_plugin('Cpp', '', '').CONFIG_JS, 'configPluginCpp')

    def test_language_and_service_base_survive_load_and_reload(self):
        config = json.dumps({'language': 'c', 'validation': 'tests', 'cpuTime': 11})
        for path in ('loadplugindto', 'reloadplugindto'):
            response = self.client.post('/open/' + path, json={'typ': 'Cpp', 'name': 'test', 'config': config})
            self.assertEqual(response.status_code, 200, response.text)
            dto = response.json()
            self.assertEqual(dto['params']['serviceBase'], '/plugincpp')
            self.assertEqual(json.loads(base64.b64decode(dto['jsonData']))['language'], 'c')

    def test_separate_help_and_static_resources(self):
        with patch.dict(os.environ, {'RESOURCE_DIR': str(RESOURCES)}):
            self.assertIn('C/C++ programming questions', self.client.get('/plugincpp/help').text)
            app = FastAPI()
            install_static_resources(app, '/pluginpython')
            install_static_resources(app, '/plugincpp', 'Cpp', root_alias=False)
            client = TestClient(app)
            self.assertIn('function initPluginCpp', client.get('/plugincpp/static/CppScript.js').text)
            self.assertEqual(client.get('/pluginpython/static/CppScript.js').status_code, 404)
            self.assertEqual(client.get('/plugincpp/static/PythonScript.js').status_code, 404)
            for name in ('cpp-logo.png', 'unittest-logo.png'):
                response = client.get('/plugincpp/static/' + name)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers['content-type'], 'image/png')
                self.assertEqual(response.content, (RESOURCES / 'plugins/Cpp' / name).read_bytes())
            self.assertEqual((RESOURCES / 'plugins/Cpp/unittest-logo.png').read_bytes(),
                             (RESOURCES / 'plugins/Python/unittest-logo.png').read_bytes())

    def test_shared_formatter_assets_support_service_prefixes(self):
        with patch.dict(os.environ, {'RESOURCE_DIR': str(RESOURCES)}):
            app = FastAPI()
            install_static_resources(app, '/custom/python')
            install_static_resources(app, '/custom/cpp', 'Cpp', root_alias=False)
            client = TestClient(app)
            for prefix in ('/custom/python', '/custom/cpp', ''):
                response = client.get(prefix + '/static/formatting/client.js')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, (RESOURCES / 'formatting/client.js').read_bytes())

    def test_cpp_development_dialog(self):
        with patch.dict(os.environ, {'RESOURCE_DIR': str(RESOURCES), 'PLUGIN_DEV_UI': 'true'}):
            app = FastAPI()
            install_dev_ui(app, '/plugincpp', 'Cpp')
        text = TestClient(app).get('/plugincpp/dev/config').text
        self.assertIn('CppConfigScript.js', text)
        self.assertIn('configPluginCpp', text)

    def test_configuration_state_has_cpp_help_and_callback(self):
        with patch.dict(os.environ, {'RESOURCE_DIR': str(RESOURCES)}):
            state = main.create_or_update_configuration_state(
                'cpp-test-state', typ='Cpp', plugin_python=main.PluginCpp('', ''))
        try:
            self.assertEqual(state.pluginConfigurationInfoDto.javaScriptMethode, 'configPluginCpp')
            self.assertEqual(state.pluginConfigDto.params['serviceBase'], '/plugincpp')
            self.assertIn('C/C++ programming questions', state.pluginConfigDto.params['help'])
            self.assertNotIn('Linter presets', state.pluginConfigDto.params['help'])
        finally:
            main.CONFIG_STATES.pop('cpp-test-state', None)

    def test_execution_requires_authentication(self):
        for endpoint in ('run', 'compile', 'check', 'scorePlugin', 'example'):
            self.assertEqual(self.client.post('/plugincpp/' + endpoint, json={'code': ''}).status_code, 401)

    def test_run_uses_correct_language_flags_files_and_cpu_time(self):
        for language, standard in [('c', '-std=c17'), ('cpp', '-std=c++17')]:
            with patch.object(cpp, 'JobeWrapper') as wrapper:
                wrapper.createFiles.return_value = []
                wrapper.return_value.run_test.return_value = MagicMock(timings={})
                response = self.client.post('/plugincpp/run', headers=self.headers, json={
                    'code': 'int main() { return 0; }',
                    'questionConfigDto': {'language': language, 'cpuTime': 9}})
                self.assertEqual(response.status_code, 200, response.text)
                args, kwargs = wrapper.return_value.run_test.call_args
                self.assertEqual(args[0], language)
                self.assertEqual(args[1], 'int main() { return 0; }')
                self.assertEqual(kwargs['cputime'], 9)
                self.assertIn(standard, kwargs['parameters']['compileargs'])

    def test_compile_supports_function_answers_and_reports_diagnostics(self):
        from shared.jobe_wrapper import RunResult
        for language in ('c', 'cpp'):
            for outcome in (15, 11):
                with self.subTest(language=language, outcome=outcome), patch.object(cpp, 'JobeWrapper') as wrapper:
                    wrapper.return_value.run_test.return_value = RunResult({
                        'outcome': outcome, 'cmpinfo': 'answer: invalid syntax' if outcome == 11 else ''})
                    response = self.client.post('/plugincpp/compile', headers=self.headers, json={
                        'code': 'int answer(void) { return 42; }',
                        'questionConfigDto': {'language': language, 'cpuTime': 9,
                                              'files': {'numbers.h': 'int number;'}}})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['success'], outcome == 15)
                    self.assertIn('Compilation successful.' if outcome == 15 else 'invalid syntax',
                                  response.json()['output'])
                    self.assertIn('Compiler output:', response.json()['output'])
                    self.assertEqual(response.json()['compilerOutput'],
                                     'answer: invalid syntax' if outcome == 11 else '')
                    if outcome == 15:
                        self.assertIn('(no compiler diagnostics)', response.json()['output'])
                    args, kwargs = wrapper.return_value.run_test.call_args
                    self.assertEqual(args[:2], ('compile' + language, 'int answer(void) { return 42; }'))
                    self.assertEqual(kwargs['cputime'], 9)
                    self.assertEqual(kwargs['files'][0][1:], ('numbers.h', b'int number;'))

    def test_compile_rejects_invalid_requests(self):
        for body in ([], {}, {'code': '', 'questionConfigDto': {'language': 'python'}}):
            response = self.client.post('/plugincpp/compile', headers=self.headers, json=body)
            self.assertEqual(response.status_code, 400, response.text)

    def test_check_and_score_use_catch2(self):
        with patch.object(cpp, 'check_catch2', return_value=CheckResult({'count': 2, 'failure_count': 1})) as check:
            for endpoint in ('check', 'scorePlugin'):
                response = self.client.post('/plugincpp/' + endpoint, headers=self.headers, json={
                    'code': 'answer', 'testcode': 'tests', 'questionConfigDto': {'language': 'c'}})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()['score'], 0.5)
                self.assertEqual(check.call_args.kwargs['language'], 'c')

    def test_invalid_language_and_missing_tests_are_rejected(self):
        for body in ({'code': '', 'questionConfigDto': {'language': 'python'}}, {'code': ''}):
            response = self.client.post('/plugincpp/check', headers=self.headers, json=body)
            self.assertEqual(response.status_code, 400)

    def test_plugin_scoring_uses_c_linkage_and_weighted_case_score(self):
        with patch.object(main, 'check_catch2', return_value=CheckResult({'count': 2, 'failure_count': 1})) as check:
            result = main.PluginCpp('', '').score('answer', None, None, 6,
                                                 config=json.dumps({'language': 'c', 'validation': 'tests', 'cpuTime': 12}))
        self.assertEqual(result.punkteIst, 3)
        self.assertEqual(result.status, 'TEILWEISE_OK')
        self.assertEqual(check.call_args.kwargs['language'], 'c')
        self.assertEqual(check.call_args.kwargs['cputime'], 12)

    def test_examples_are_separate_and_language_aware(self):
        for language in ('c', 'cpp'):
            entries = cpp_examples(language)
            for index, entry in enumerate(entries):
                dropdown_index = index + (len(EXAMPLE_NAMES) if language == 'cpp' else 0)
                response = self.client.post('/plugincpp/example', headers=self.headers,
                                            json={'index': dropdown_index, 'questionConfigDto': {'language': 'cpp' if language == 'c' else 'c'}})
                self.assertEqual(response.json()['names'], list(EXAMPLE_NAMES) * 2)
                self.assertEqual(response.json()['languages'], ['c'] * len(EXAMPLE_NAMES) + ['cpp'] * len(EXAMPLE_NAMES))
                self.assertEqual(response.json()['count'], 2 * len(EXAMPLE_NAMES))
                self.assertEqual(response.json()['output'], entry)
                folder = RESOURCES.parent / 'examples/CPP' / EXAMPLE_NAMES[index]
                self.assertEqual(entry['title'], folder.name)
                template = folder / ('template.c' if language == 'c' else 'template.cpp')
                if not template.exists():
                    template = folder / 'template.cpp'
                self.assertEqual(entry['indication'], template.read_text(encoding='utf-8'))
                self.assertEqual(entry['validation'], (folder / 'test_answer.cpp').read_text(encoding='utf-8'))
                self.assertIn('catch2/catch_test_macros.hpp', entry['validation'])
                self.assertIn('#if __has_include("answer.c")', entry['validation'])
                self.assertFalse({'template.c', 'template.cpp', 'answer.c', 'answer.cpp'} & entry['files'].keys())
            self.assertEqual(entries[2]['files']['number.txt'], '42\n')
            self.assertIn('counter.h', entries[EXAMPLE_NAMES.index('counter')]['files'])
            self.assertEqual(entries[EXAMPLE_NAMES.index('read_text')]['files']['names.txt'], 'Ada\nRenée\nLin\n')
        self.assertEqual([entry['validation'] for entry in cpp_examples('c')],
                         [entry['validation'] for entry in cpp_examples('cpp')])


class TestCppPluginIntegration(unittest.TestCase):
    """Requires the development Jobe service at localhost:4000."""

    def test_compile_checks_code_without_linking_or_running(self):
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        cases = [
            ('int answer(void) { return 42; }', True),
            ('#include "number.h"\nint answer(void) { return NUMBER; }', True),
            ('int main(void) { for (;;) {} }', True),
            ('int main(void) { return 1; }', True),
            ('int answer(void) { return ; }', False),
        ]
        with patch.object(cpp, 'JOBE_SERVER', '127.0.0.1:4000'):
            for language in ('c', 'cpp'):
                for code, success in cases:
                    with self.subTest(language=language, code=code):
                        response = client.post('/plugincpp/compile', headers=headers, json={
                            'code': code, 'questionConfigDto': {'language': language,
                                'files': {'number.h': '#define NUMBER 42\n'}}})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()['success'], success, response.text)

    def test_examples_grade_completed_c_and_cpp_answers_through_endpoints(self):
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        with patch.object(cpp, 'JOBE_SERVER', '127.0.0.1:4000'):
            for language in ('c', 'cpp'):
                for config in cpp_examples(language):
                    if config['title'] == 'dataset_numbers':
                        config['datasetVariables'] = [
                            {'name': 'a', 'value': 3}, {'name': 'n', 'value': 4}]
                    folder = RESOURCES.parent / 'examples/CPP' / config['title']
                    answer = folder / ('answer.c' if language == 'c' else 'answer.cpp')
                    if not answer.exists():
                        answer = folder / 'answer.cpp'
                    solution = answer.read_text(encoding='utf-8')
                    with self.subTest(language=language, example=config['title']):
                        response = client.post('/plugincpp/check', headers=headers, json={
                            'code': solution, 'testcode': config['validation'], 'questionConfigDto': config})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()['score'], 1.0, response.text)

    def test_unfinished_examples_compile_but_fail_behavior_checks(self):
        from shared.check_catch2 import check_catch2
        from shared.jobe_wrapper import JobeWrapper
        for language in ('c', 'cpp'):
            for config in cpp_examples(language):
                with self.subTest(language=language, example=config['title']):
                    files = JobeWrapper.createFiles({name: content.encode('utf-8')
                                                    for name, content in config['files'].items()})
                    if config['title'] == 'dataset_numbers':
                        from app.dataset_helper import DatasetVariable
                        from shared.cpp_dataset import cpp_dataset_files
                        files += JobeWrapper.createFiles(cpp_dataset_files([
                            DatasetVariable('a', 3), DatasetVariable('n', 4)], language))
                    result = check_catch2('127.0.0.1:4000', config['indication'],
                                          config['validation'], language=language, files=files)
                    self.assertGreater(result.count, 0, repr(result))
                    self.assertFalse(result.wasSuccessful(), repr(result))

    def test_dataset_numbers_uses_current_values_and_exact_output(self):
        from shared.check_catch2 import check_catch2
        from shared.cpp_dataset import cpp_dataset_files
        from shared.jobe_wrapper import JobeWrapper
        from app.dataset_helper import DatasetVariable

        for language in ('c', 'cpp'):
            config = cpp_examples(language)[EXAMPLE_NAMES.index('dataset_numbers')]
            folder = RESOURCES.parent / 'examples/CPP/dataset_numbers'
            solution = (folder / ('answer.c' if language == 'c' else 'answer.cpp')).read_text(encoding='utf-8')
            self.assertNotIn('dataset.h', config['files'])
            self.assertEqual(config['datasetVariables'], [])
            for a, n in ((3, 4), (-3, 2), (7, 0), (0, 100)):
                with self.subTest(language=language, a=a, n=n):
                    files = JobeWrapper.createFiles(cpp_dataset_files([
                        DatasetVariable('a', a), DatasetVariable('n', n)], language))
                    result = check_catch2('127.0.0.1:4000', solution,
                                          config['validation'], language=language, files=files)
                    self.assertEqual(result.count, 1, repr(result))
                    self.assertTrue(result.wasSuccessful(), repr(result))

            files = JobeWrapper.createFiles(cpp_dataset_files([
                DatasetVariable('a', -3), DatasetVariable('n', 2)], language))
            for wrong in (
                '#include <stdio.h>\nvoid print_numbers(int a, int b) { '
                'for (int i = a; i < b; ++i) printf("%d\\n", i); }',
                '#include <stdio.h>\nvoid print_numbers(int a, int b) { '
                '(void)a; (void)b; printf("3\\n4\\n5\\n6\\n7\\n"); }',
                '#include <stdio.h>\nvoid print_numbers(int a, int b) { '
                'for (int i = a; i <= b; ++i) printf("%d ", i); }',
                '#include <stdio.h>\nvoid print_numbers(int a, int n) { '
                'for (int i = 0; i <= n; ++i) printf("%d\\n", a + i); }',
            ):
                with self.subTest(language=language, wrong=wrong):
                    result = check_catch2('127.0.0.1:4000', wrong,
                                          config['validation'], language=language, files=files)
                    self.assertEqual(result.count, 1, repr(result))
                    self.assertFalse(result.wasSuccessful(), repr(result))
                    self.assertEqual(result.score(), 0, repr(result))

    def test_run_returns_stdout_for_both_languages(self):
        client = TestClient(main.app)
        with patch.object(cpp, 'JOBE_SERVER', '127.0.0.1:4000'):
            for language in ('c', 'cpp'):
                response = client.post('/plugincpp/run', headers={'Authorization': 'Bearer ' + common.get_exec_token()},
                                       json={'code': '#include <stdio.h>\nint main(void) { puts("Cpp plugin"); return 0; }',
                                             'questionConfigDto': {'language': language}})
                self.assertEqual(response.status_code, 200, response.text)
                self.assertIn('Cpp plugin', response.json()['output'])
                self.assertNotIn('Compile error', response.json()['output'])
