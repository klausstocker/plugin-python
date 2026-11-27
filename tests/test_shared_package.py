"""Exercise assets needed when shared is installed without the service sources."""
import importlib
import subprocess
import sys
import unittest
from unittest.mock import patch

from shared.check import _with_student_answer_file
from shared.check_sql import sql_program
from shared.cpp_dataset import cpp_dataset_files
from shared.cpp_examples import cpp_examples
from shared.dataset_helper import DatasetVariable
from shared.question_examples import QuestionConfigDtoExamples
from shared.sql_examples import EXAMPLE_NAMES, sql_example


class TestSharedPackage(unittest.TestCase):
    def test_python_helper_is_uploaded_from_package(self):
        with patch('shared.check.JobeWrapper.createFiles', side_effect=lambda files: [files]) as create:
            _with_student_answer_file('print(42)')
        self.assertIn(b'class RedirectedStdout', create.call_args.args[0]['helpers.py'])

    def test_sql_runner_source_is_available(self):
        result = subprocess.run(
            [sys.executable, '-I', '-c', sql_program('SELECT 42 AS answer;')],
            capture_output=True, text=True, check=True)
        self.assertIn('(42,)', result.stdout)

    def test_examples_and_cpp_support_are_available(self):
        self.assertTrue(all(example.indication and example.validation
                            for example in QuestionConfigDtoExamples()))
        for language in ('c', 'cpp'):
            self.assertTrue(all(example['indication'] and example['validation']
                                for example in cpp_examples(language)))
            files = cpp_dataset_files([DatasetVariable('n', 42, 'm')], language)
            self.assertIn(b'42.0f', files['dataset.h'])
            self.assertTrue(files['helpers.h'])
            self.assertTrue(files['helpers.c'])
        for index in range(len(EXAMPLE_NAMES)):
            self.assertTrue(sql_example(index).preparation)
            self.assertTrue(sql_example(index, solution=True).validation)

    def test_app_dataset_imports_preserve_class_identity(self):
        legacy = importlib.import_module('app.dataset_helper')
        self.assertIs(legacy.DatasetVariable, DatasetVariable)

    def test_lint_endpoint_uses_installed_pylint(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.code_execution_endpoints import get_exec_token

        response = TestClient(app).post(
            '/pluginpython/lint',
            headers={'Authorization': 'Bearer ' + get_exec_token()},
            json={'code': 'print(undefined_package_test_name)\n'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('E0602', response.json()['output'])
