import base64
import json
import os
import subprocess
import unittest
import uuid
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app import main
from app import code_execution_endpoints as common
from shared.compiler_flags import parse_compiler_flags
from shared.formatting import format_source, FormatterUnavailable
from shared.question_config import CppQuestionConfigDto, QuestionConfigDto
from shared.jobe_wrapper import RunResult


class TestFormattingEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.headers = {'Authorization': 'Bearer ' + common.get_exec_token()}

    def test_each_endpoint_requires_authentication(self):
        for prefix in ('pluginpython', 'plugincpp'):
            self.assertEqual(self.client.post('/' + prefix + '/format', json={'code': ''}).status_code, 401)

    @patch('app.formatting_endpoints.format_source', return_value='formatted\n')
    def test_request_uses_question_config_and_explicit_test_language(self, formatter):
        for prefix, config, filename, language in (
            ('pluginpython', '[format]\nquote-style = "single"', 'main.py', 'python'),
            ('plugincpp', 'IndentWidth: 2', 'main.c', 'c'),
            ('plugincpp', 'IndentWidth: 2', 'main.cpp', 'cpp'),
        ):
            response = self.client.post('/' + prefix + '/format', headers=self.headers, json={
                'code': 'original', 'filename': filename,
                'questionConfigDto': {'language': 'c', 'formatterConfig': config}})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['code'], 'formatted\n')
            self.assertGreaterEqual(response.json()['timings']['format_seconds'], 0)
            formatter.assert_called_with('original', language, config)

    @patch('app.formatting_endpoints.format_source', return_value='')
    def test_cpp_defaults_to_question_language(self, formatter):
        response = self.client.post('/plugincpp/format', headers=self.headers, json={
            'code': '', 'questionConfigDto': {'language': 'c'}})
        self.assertEqual(response.status_code, 200)
        formatter.assert_called_with('', 'c', '')

    @patch('app.formatting_endpoints.format_source')
    def test_invalid_requests_never_invoke_formatter(self, formatter):
        for prefix in ('pluginpython', 'plugincpp'):
            for body in ([], {}, {'code': 123}, {'code': 'x' * 131073},
                         {'code': '', 'filename': '../file.py'},
                         {'code': '', 'questionConfigDto': {'formatterConfig': 'x' * 16385}}):
                response = self.client.post('/' + prefix + '/format', headers=self.headers, json=body)
                self.assertEqual(response.status_code, 400, response.text)
        formatter.assert_not_called()

    def test_tool_errors_return_no_replacement_code(self):
        for error, status in ((ValueError('syntax error'), 400),
                              (FormatterUnavailable('missing tool'), 503),
                              (subprocess.TimeoutExpired('ruff', 5), 504)):
            with patch('app.formatting_endpoints.format_source', side_effect=error):
                response = self.client.post('/pluginpython/format', headers=self.headers, json={'code': ''})
            self.assertEqual(response.status_code, status)
            self.assertNotIn('code', response.json())

    def test_settings_survive_load_reload_and_encoded_config(self):
        for typ, model in (('Python', QuestionConfigDto), ('Cpp', CppQuestionConfigDto)):
            config = {'formatterConfig': 'saved config'}
            if typ == 'Cpp':
                config['compilerFlags'] = '-O2 -DNUMBER=42'
            encoded = main.encode_question_config_base64(json.dumps(config), model)
            decoded = json.loads(base64.b64decode(encoded))
            for name, value in config.items():
                self.assertEqual(decoded[name], value)
            for operation in ('loadplugindto', 'reloadplugindto'):
                response = self.client.post('/open/' + operation, json={
                    'typ': typ, 'name': 'format-config', 'config': json.dumps(config)})
                self.assertEqual(response.status_code, 200, response.text)
                decoded = json.loads(base64.b64decode(response.json()['jsonData']))
                for name, value in config.items():
                    self.assertEqual(decoded[name], value)


class TestPluginFormattingIntegration(unittest.TestCase):
    """Uses the formatters in the normal running plugin, without local tools."""

    def setUp(self):
        server = os.environ.get('PLUGIN_TEST_SERVER', 'http://localhost:8209')
        self.client = httpx.Client(base_url=server.rstrip('/'), timeout=10)
        self.addCleanup(self.client.close)
        response = self.client.get('/pluginpython/exectoken')
        self.assertEqual(response.status_code, 200, response.text)
        self.client.headers['Authorization'] = 'Bearer ' + response.json()['token']

    def format(self, code, filename, config=''):
        prefix = '/pluginpython' if filename.endswith('.py') else '/plugincpp'
        response = self.client.post(prefix + '/format', json={
            'code': code, 'filename': filename,
            'questionConfigDto': {'formatterConfig': config}})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['code']

    def test_ruff_uses_question_options_and_is_idempotent(self):
        config = 'indent-width = 2\n[format]\nquote-style = "single"'
        code = 'def greet( ):\n return "Grüße"'
        formatted = self.format(code, 'main.py', config)
        self.assertEqual(formatted, "def greet():\n  return 'Grüße'\n")
        self.assertEqual(self.format(formatted, 'main.py', config), formatted)
        response = self.client.post('/pluginpython/format', json={'code': 'def broken(:'})
        self.assertEqual(response.status_code, 400, response.text)
        self.assertNotIn('code', response.json())

    def test_clang_uses_question_options_and_is_idempotent(self):
        config = 'BasedOnStyle: LLVM\nIndentWidth: 2\nAllowShortFunctionsOnASingleLine: None'
        for language in ('c', 'cpp'):
            formatted = self.format('int sum(int a,int b){return a+b;}\n', 'main.' + language, config)
            self.assertEqual(formatted, 'int sum(int a, int b) {\n  return a + b;\n}\n')
            self.assertEqual(self.format(formatted, 'main.' + language, config), formatted)
        response = self.client.post('/plugincpp/format', json={
            'code': 'int main(){}', 'filename': 'main.cpp',
            'questionConfigDto': {'formatterConfig': 'UnknownClangOption: true'}})
        self.assertEqual(response.status_code, 400, response.text)
        self.assertNotIn('code', response.json())


class TestFormatterConfiguration(unittest.TestCase):
    @patch('shared.formatting.subprocess.run')
    def test_external_configs_are_rejected_before_tool_start(self, run):
        for config in ('extend = "/etc/ruff.toml"', '"/etc/ruff.toml"', 'cache-dir = "/tmp/x"'):
            with self.assertRaises(ValueError):
                format_source('', 'python', config)
        with self.assertRaises(ValueError):
            format_source('', 'cpp', 'BasedOnStyle: InheritParentConfig')
        run.assert_not_called()


class TestCompilerFlags(unittest.TestCase):
    def test_flags_reach_run_compile_check_and_score(self):
        from app import cpp_execution_endpoints as cpp
        from shared.check_result import CheckResult
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        body = {'code': 'code', 'testcode': 'tests', 'questionConfigDto': {
            'compilerFlags': '-O2 -Wextra -DNUMBER=42', 'language': 'c'}}
        with patch.object(cpp, 'JobeWrapper') as wrapper:
            wrapper.return_value.run_test.return_value = RunResult({'outcome': 15})
            for operation in ('run', 'compile'):
                response = client.post('/plugincpp/' + operation, headers=headers, json=body)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(wrapper.return_value.run_test.call_args.kwargs['parameters']['compileargs'],
                                 ['-std=c17', '-Wall', '-Werror', '-O2', '-Wextra', '-DNUMBER=42'])
        with patch.object(cpp, 'check_catch2', return_value=CheckResult({'count': 1})) as check:
            for operation in ('check', 'scorePlugin'):
                self.assertEqual(client.post('/plugincpp/' + operation, headers=headers, json=body).status_code, 200)
                self.assertEqual(check.call_args.kwargs['compiler_flags'], body['questionConfigDto']['compilerFlags'])

    def test_flags_reach_catch2_submission_and_lettos_grading(self):
        from shared.check_catch2 import check_catch2
        from shared.jobe_wrapper import JobeWrapper, RunResult
        from shared.check_result import CheckResult
        report = '__catch2_report__\n<Catch2TestRun><OverallResultsCases successes="1" failures="0"/></Catch2TestRun>'
        with patch.object(JobeWrapper, 'run_test', return_value=RunResult({'outcome': 15, 'stdout': report})) as run:
            check_catch2('unused', 'code', 'tests', compiler_flags='-DNUMBER=42')
            self.assertEqual(run.call_args.kwargs['parameters'], {'compileargs': ['-DNUMBER=42']})
        with patch.object(main, 'check_catch2', return_value=CheckResult({'count': 1})) as check:
            main.PluginCpp('', '').score('code', None, None, 1, config=json.dumps({'compilerFlags': '-DNUMBER=42'}))
            self.assertEqual(check.call_args.kwargs['compiler_flags'], '-DNUMBER=42')

    def test_unsafe_flags_are_rejected_before_jobe(self):
        from app import cpp_execution_endpoints as cpp
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        for flags in ('-O2;touch bad', '-fplugin=/tmp/plugin.so', '@args', '-o output',
                      '-I/etc', '-I../', '-Wl,-plugin,/tmp/plugin.so', '-DVALUE=$(command)'):
            with self.subTest(flags=flags), patch.object(cpp, 'JobeWrapper') as wrapper:
                response = client.post('/plugincpp/run', headers=headers, json={
                    'code': 'code', 'questionConfigDto': {'compilerFlags': flags}})
                self.assertEqual(response.status_code, 400, response.text)
                wrapper.assert_not_called()
        self.assertEqual(parse_compiler_flags('-O2 -Wno-error -std=c++20 -Iinclude -DNUMBER=42'),
                         ['-O2', '-Wno-error', '-std=c++20', '-Iinclude', '-DNUMBER=42'])


class TestCompilerFlagsIntegration(unittest.TestCase):
    """Uses the project's Jobe service, with an optional address override."""

    def setUp(self):
        self.server = os.environ.get('JOBE_TEST_SERVER', 'localhost:4000')

    def test_custom_flags_affect_real_run_compile_check_and_score(self):
        from app import cpp_execution_endpoints as cpp
        from shared.cpp_examples import cpp_examples
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        with patch.object(cpp, 'JOBE_SERVER', self.server):
            for language in ('c', 'cpp'):
                question = {'language': language, 'compilerFlags': '-DNUMBER=42'}
                for operation in ('run', 'compile'):
                    response = client.post('/plugincpp/' + operation, headers=headers, json={
                        'code': '#include <stdio.h>\nint main(void) { printf("%d", NUMBER); return 0; }',
                        'questionConfigDto': question})
                    self.assertEqual(response.status_code, 200, response.text)
                    if operation == 'compile':
                        self.assertTrue(response.json()['success'], response.text)
                    else:
                        self.assertIn('42', response.json()['output'])
                question['compilerFlags'] += ' -std=c11' if language == 'c' else ' -std=c++20'
                # A C++20-only expression proves the standard override takes effect.
                answer = 'int calculate_sum(int a, int b) { return a + b; }'
                if language == 'cpp':
                    answer = '#include <concepts>\nstatic_assert(std::integral<int>);\n' + answer
                for operation in ('check', 'scorePlugin'):
                    response = client.post('/plugincpp/' + operation, headers=headers, json={
                        'code': answer, 'testcode': cpp_examples(language)[0]['validation'],
                        'questionConfigDto': question})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(response.json()['score'], 1, response.text)

    def test_effective_flags_invalidate_catch2_cache(self):
        from shared.jobe_wrapper import JobeWrapper
        from shared.check_catch2 import parse_catch2_report
        testcode = ('#include <catch2/catch_test_macros.hpp>\nint answer();\n'
                    'TEST_CASE("' + uuid.uuid4().hex + '") { REQUIRE(answer() == NUMBER); }')
        hits = []
        for value in (42, 42, 43):
            result = JobeWrapper(self.server).run_test(
                'catch2cpp', testcode, 'test.cpp',
                files=JobeWrapper.createFiles({'answer.cpp': b'int answer() { return NUMBER; }'}),
                parameters={'compileargs': [f'-DNUMBER={value}']})
            self.assertTrue(result.success(), repr(result))
            self.assertTrue(parse_catch2_report(result.stdout).wasSuccessful())
            hits.append(result.timings['test_cache_hit'])
        self.assertEqual(hits, [False, True, False])
