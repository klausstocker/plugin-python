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
from shared.cpp_examples import cpp_examples

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
        for endpoint in ('run', 'check', 'scorePlugin', 'example'):
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
                self.assertEqual(kwargs['cputime'], 9)
                self.assertIn(standard, kwargs['parameters']['compileargs'])

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
                response = self.client.post('/plugincpp/example', headers=self.headers,
                                            json={'index': index, 'questionConfigDto': {'language': language}})
                self.assertEqual(response.json()['output'], entry)
                self.assertIn('catch2/catch_test_macros.hpp', entry['validation'])
                self.assertIn('#if __has_include("answer.c")', entry['validation'])
                self.assertIn('#define ANSWER_LINKAGE extern "C"', entry['validation'])
            self.assertEqual(entries[2]['files']['number.txt'], '42\n')
        self.assertEqual([entry['validation'] for entry in cpp_examples('c')],
                         [entry['validation'] for entry in cpp_examples('cpp')])


class TestCppPluginIntegration(unittest.TestCase):
    """Requires the development Jobe service at localhost:4000."""

    def test_examples_grade_completed_c_and_cpp_answers_through_endpoints(self):
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        solutions = [
            'int calculate_sum(int a, int b) { return a + b; }',
            '#include <stdio.h>\nvoid print_message(void) { puts("Hello!"); }',
            '#include <stdio.h>\nint read_number(void) { FILE* f = fopen("number.txt", "r"); '
            'if (!f) return -1; int value = 0; fscanf(f, "%d", &value); fclose(f); return value; }',
        ]
        with patch.object(cpp, 'JOBE_SERVER', '127.0.0.1:4000'):
            for language in ('c', 'cpp'):
                # Reuse the same tests after switching language, without reloading.
                for original_config, solution in zip(cpp_examples('cpp'), solutions):
                    config = dict(original_config, language=language)
                    with self.subTest(language=language, example=config['title']):
                        response = client.post('/plugincpp/check', headers=headers, json={
                            'code': solution, 'testcode': config['validation'], 'questionConfigDto': config})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()['score'], 1.0, response.text)

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
