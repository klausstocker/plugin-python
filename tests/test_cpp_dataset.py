"""Dataset unit tests and integration checks using the normal project Jobe."""
import json
import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main, cpp_execution_endpoints as cpp, code_execution_endpoints as common
from app.dataset_helper import DatasetVariable
from shared.check_catch2 import parse_catch2_report
from shared.check_result import CheckResult
from shared.cpp_dataset import cpp_dataset_files
from shared.jobe_wrapper import JobeWrapper, RunResult


class TestCppDataset(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.headers = {'Authorization': 'Bearer ' + common.get_exec_token()}

    def test_run_and_compile_exclude_even_uploaded_datasets(self):
        for language in ('c', 'cpp'):
            for operation in ('run', 'compile'):
                with self.subTest(language=language, operation=operation), patch.object(
                        JobeWrapper, 'run_test', return_value=RunResult({'outcome': 15})) as run:
                    response = self.client.post('/plugincpp/' + operation, headers=self.headers, json={
                        'code': 'int main(void) { return 0; }', 'questionConfigDto': {
                            'language': language, 'files': {'dataset.h': 'stale', 'helpers.h': 'stale'},
                            'datasetVariables': [{'name': 'text', 'value': 'not numeric'}]}})
                    self.assertEqual(response.status_code, 200, response.text)
                    files = {name: contents for _, name, contents in run.call_args.kwargs['files']}
                    self.assertEqual(set(files), {'helpers.h'})
                    self.assertNotIn(b'stale', files['helpers.h'])

    def test_check_and_score_replace_uploaded_headers_with_current_values(self):
        for language in ('c', 'cpp'):
            for operation in ('check', 'scorePlugin'):
                with self.subTest(language=language, operation=operation), patch.object(
                        cpp, 'check_catch2', return_value=CheckResult({'count': 1})) as check:
                    response = self.client.post('/plugincpp/' + operation, headers=self.headers, json={
                        'code': 'answer', 'testcode': 'tests', 'questionConfigDto': {
                            'language': language, 'files': {'dataset.h': 'stale', 'helpers.h': 'stale'},
                            'datasetVariables': [{'name': 'speed', 'value': 12.5, 'unit': 'm/s'}]}})
                    self.assertEqual(response.status_code, 200, response.text)
                    files = {name: contents for _, name, contents in check.call_args.kwargs['files']}
                    self.assertNotIn(b'stale', files['helpers.h'])
                    self.assertIn(b'12.5f', files['dataset.h'])
                    self.assertIn(b'"speed"', files['dataset.h'])
                    self.assertIn(b'"m/s"', files['dataset.h'])
                    self.assertNotIn('dataset.py', files)

    def test_grading_ignores_saved_dataset_snapshots(self):
        for language in ('c', 'cpp'):
            config = json.dumps({'language': language, 'validation': 'tests',
                                 'datasetVariables': [{'name': 'speed', 'value': 999}],
                                 'files': {'dataset.h': 'stale', 'helpers.h': 'stale'}})
            for current in (main.VarHashDto.model_validate({
                    'vars': {'speed': {'calcErgebnisDto': {'json': '{"d":14}'}}}}), None):
                with self.subTest(language=language, current=current), patch.object(
                        main, 'check_catch2', return_value=CheckResult({'count': 1})) as check:
                    result = main.PluginCpp('', '').score('answer', None, None, 2,
                                                          config=config, varsQuestion=current)
                    self.assertEqual(result.punkteIst, 2)
                    files = {name: contents for _, name, contents in check.call_args.kwargs['files']}
                    self.assertNotIn(b'999', files['dataset.h'])
                    self.assertNotIn(b'stale', files['dataset.h'])
                    if current is not None:
                        self.assertIn(b'14.0f', files['dataset.h'])
                    else:
                        self.assertNotIn(b'"speed"', files['dataset.h'])

    def test_invalid_numeric_data_is_reported_before_jobe(self):
        for value in ('text', None, 1e100):
            with self.subTest(value=value), patch.object(cpp, 'check_catch2') as check:
                response = self.client.post('/plugincpp/check', headers=self.headers, json={
                    'code': 'answer', 'testcode': 'tests',
                    'questionConfigDto': {'datasetVariables': [{'name': 'speed', 'value': value}]}})
                self.assertEqual(response.status_code, 400, response.text)
                self.assertIn('speed', response.json()['output'])
                check.assert_not_called()

    def test_headers_are_downloadable_from_help_with_service_prefixes(self):
        from pathlib import Path
        from fastapi import FastAPI
        from app.static_resources import install_static_resources
        resources = Path(__file__).resolve().parents[1] / 'resources'
        with patch.dict(os.environ, {'RESOURCE_DIR': str(resources)}):
            app = FastAPI()
            install_static_resources(app, '/custom/cpp', 'Cpp', root_alias=False)
            response = TestClient(app).get('/custom/cpp/static/helpers.h')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, (resources / 'plugins/Cpp/helpers.h').read_bytes())
            help_text = self.client.get('/plugincpp/help').text
            self.assertIn('data-plugin-help-file="helpers.h"', help_text)
            self.assertIn('download="helpers.h"', help_text)


class TestCppDatasetIntegration(unittest.TestCase):
    def setUp(self):
        self.server = os.environ.get('JOBE_TEST_SERVER', 'localhost:4000')

    def test_teacher_checks_and_grading_use_each_students_dataset(self):
        client = TestClient(main.app)
        headers = {'Authorization': 'Bearer ' + common.get_exec_token()}
        # The answer uses ordinary function arguments, with no dataset imports.
        answer = 'float double_value(float value) { return value * 2; }'
        for language in ('c', 'cpp'):
            linkage = 'extern "C" ' if language == 'c' else ''
            get_value = 'const variable *number = dataset_get("number"); REQUIRE(number != nullptr);'
            tests = ('#include <catch2/catch_test_macros.hpp>\n#include "dataset.h"\n'
                     '#include <cstring>\n' + linkage + 'float double_value(float);\n'
                     'TEST_CASE("dataset") { ' + get_value +
                     ' REQUIRE(double_value(number->value) == number->value * 2); '
                     ' REQUIRE(std::strcmp(number->unit, "m/s") == 0); }')
            for value in (7, -3.5):
                with self.subTest(language=language, value=value), patch.object(cpp, 'JOBE_SERVER', self.server):
                    current_tests = tests.replace('REQUIRE(double_value',
                                                  f'REQUIRE(number->value == {float(value)}f); REQUIRE(double_value')
                    config = {'language': language, 'validation': current_tests,
                              'datasetVariables': [{'name': 'number', 'value': value, 'unit': 'm/s'}]}
                    for operation in ('check', 'scorePlugin'):
                        response = client.post('/plugincpp/' + operation, headers=headers,
                                               json={'code': answer, 'testcode': current_tests, 'questionConfigDto': config})
                        self.assertEqual(response.status_code, 200, response.text)
                        self.assertEqual(response.json()['score'], 1, response.text)
                    current = main.VarHashDto.model_validate({'vars': {'number': {
                        'calcErgebnisDto': {'json': json.dumps({'d': value, 'originalEinheitString': 'm/s'})}}}})
                    # A stale preview value must not replace the student's current data.
                    config['datasetVariables'][0]['value'] = 999
                    with patch.dict(os.environ, {'JOBE_SERVER': self.server}):
                        score = main.PluginCpp('', '').score(answer, None, None, 2,
                                                            config=json.dumps(config), varsQuestion=current)
                    self.assertEqual(score.punkteIst, 2, score.feedback)

    def test_empty_datasets_and_special_values_compile_in_teacher_tests(self):
        for language in ('c', 'cpp'):
            for populated in (False, True):
                with self.subTest(language=language, populated=populated):
                    variables = [] if not populated else [
                        DatasetVariable('quote"\\\n??/µ9', 0.1, 'm"\\\nµ9'),
                        DatasetVariable('nan', float('nan')), DatasetVariable('inf', float('inf')),
                        DatasetVariable('tiny', 1e-100), DatasetVariable('max', 3.4028234663852886e38)]
                    if not populated:
                        assertion = 'REQUIRE(DATASET_VARIABLE_COUNT == 0); REQUIRE(dataset_get("absent") == nullptr);'
                    else:
                        assertion = (
                            'const char *name = "quote\\042\\134\\012\\077\\077/\\302\\2659";'
                            'const variable *v = dataset_get(name); REQUIRE(v != nullptr);'
                            'REQUIRE(v->value == 0.1f);'
                            'REQUIRE(std::strcmp(v->unit, "m\\042\\134\\012\\302\\2659") == 0);'
                            'REQUIRE(DATASET_VARIABLE_COUNT == 5); REQUIRE(dataset_get("absent") == nullptr);'
                            'REQUIRE(dataset_get(nullptr) == nullptr);')
                        for name, assertion_code in (('nan', 'std::isnan(v->value)'),
                                                     ('inf', 'std::isinf(v->value)'),
                                                     ('tiny', 'v->value == 0.0f'),
                                                     ('max', 'std::isfinite(v->value)')):
                            lookup = f'dataset_get("{name}")'
                            assertion += '{ const variable *v = ' + lookup + '; REQUIRE(' + assertion_code + '); }'
                    tests = ('#include <catch2/catch_test_macros.hpp>\n#include "dataset.h"\n'
                             '#include <cmath>\n#include <cstring>\nTEST_CASE("values") {' + assertion + '}')
                    files = cpp_dataset_files(variables, language)
                    files['answer.c' if language == 'c' else 'answer.cpp'] = (
                        b'#include "helpers.h"\n'
                        b'float unused(void) { variable input = {1.0f, "m/s"}; return input.value; }')
                    result = JobeWrapper(self.server).run_test('catch2' + language, tests, 'test.cpp',
                                                               files=JobeWrapper.createFiles(files))
                    self.assertTrue(result.success(), repr(result))
                    self.assertTrue(parse_catch2_report(result.stdout).wasSuccessful(), repr(result))
