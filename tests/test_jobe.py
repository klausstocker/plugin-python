import unittest
import sys
from unittest.mock import patch

from shared.jobe_wrapper import (
    CATCH2_TEST_FILENAME,
    LANGUAGE_C,
    LANGUAGE_CPP,
    JobeWrapper,
)
from shared.check import checkCode
from shared.check_result import CheckResult
from shared.question_config import QuestionConfigDto
from shared.question_examples import *


class TestJobeWrapper(unittest.TestCase):

    def test_run(self):
        code = """
MESSAGE = 'Hello Jobe!'

def sillyFunc(message):
    '''Pointless function that prints the given message'''
    print("Message is", message)

sillyFunc(MESSAGE)
"""
        jobe = JobeWrapper('localhost:4000')
        result = jobe.run_test('python3', code, 'test.py')
        self.assertTrue(result.success())

    def test_check(self):
        code = """
def calculate_sum(a, b):
    print('the sum is ' + str(a + b))
    return a + b
"""
        testCode = """
import unittest
import answer

def correctImplementation(arg1, arg2):
    sum = arg1 + arg2
    print(f'the sum is {sum}')
    return sum

class Checker(unittest.TestCase): # do not rename
    def test_return(self): # names must start with 'test_'
        args = (1, 2)
        student_result = answer.calculate_sum(*args) # call to students implementation
        expected_result = correctImplementation(*args)
        self.assertEqual(student_result, expected_result)

    def test_output(self):
        args = (3, 4)
        with RedirectedStdout() as student_out:
            answer.calculate_sum(*args)
        with RedirectedStdout() as expected_out:
            correctImplementation(*args)
        self.assertEqual(str(student_out), str(expected_out))
"""
        result = checkCode('localhost:4000', code, testCode)
        self.assertEqual(result.count, 2)
        self.assertTrue(result.wasSuccessful())

    def test_check_one_passing_one_failing(self):
        code = """
def always_true():
    return True
"""
        testCode = """
import unittest
import answer

class Checker(unittest.TestCase): # do not rename
    def test_true(self):
        self.assertTrue(answer.always_true())

    def test_false(self):
        self.assertFalse(answer.always_true())
"""
        result = checkCode('localhost:4000', code, testCode)
        self.assertEqual(result.count, 2)
        self.assertEqual(len(result.failures), 1)
        self.assertEqual(result.score(), 0.5)


    def test_check_uploads_files_to_jobe(self):
        files = [("stored-id", "input.txt", b"content")]

        class FakeRunResult:
            stdout = '__magic_string__{"count":1,"errors":[],"failures":[],"exceptions":[]}'

            def success(self):
                return True

        with patch("shared.check.JobeWrapper") as wrapper_cls:
            wrapper = wrapper_cls.return_value
            wrapper.run_test.return_value = FakeRunResult()

            testCode = """
import unittest
import answer

class Checker(unittest.TestCase):
    def test_has_answer_module(self):
        self.assertTrue(hasattr(answer, "__file__"))
"""
            result = checkCode("jobe:80", "print(open('input.txt').read())\n", testCode, files=files)

            wrapper.run_test.assert_called_once()
            submitted_code = wrapper.run_test.call_args.args[1]
            submitted_files = wrapper.run_test.call_args.args[3]
            self.assertIn("import answer", submitted_code)
            self.assertNotIn("print(open('input.txt').read())", submitted_code)
            self.assertEqual(submitted_files[0][1], "answer.py")
            self.assertEqual(submitted_files[0][2], b"print(open('input.txt').read())\n")
            self.assertEqual(submitted_files[1:], files)
            self.assertTrue(result.wasSuccessful())

    def test_run_test_reports_error_when_cpu_work_exceeds_configured_cputime(self):
        code = """
import time

deadline = time.process_time() + 2
while time.process_time() < deadline:
    pass
print('finished cpu work')
"""
        jobe = JobeWrapper('localhost:4000')

        short_result = jobe.run_test('python3', code, 'test.py', cputime=1)
        self.assertFalse(short_result.success())
        self.assertEqual(short_result.outcome()[0], 13)
        self.assertIn('Time limit exceeded', short_result.__repr__())

        long_result = jobe.run_test('python3', code, 'test.py', cputime=5)
        self.assertTrue(long_result.success())
        self.assertEqual(long_result.stdout, 'finished cpu work\n')

    def test_run_test_includes_configured_cputime_in_runspec(self):
        jobe = JobeWrapper('jobe:80')

        with patch.object(jobe, 'do_http', return_value={'outcome': 15}) as do_http:
            jobe.run_test('python3', 'print(1)', 'test.py', cputime=12, parameters={'compileargs': ['-Wall']})

        payload = do_http.call_args.args[3]
        self.assertIn('"parameters":{"compileargs":["-Wall"],"cputime":12}', payload)

    def testUpload(self):
        jobe = JobeWrapper('localhost:4000')
        fileId = 'B00WHrZtSjfile1gasdfaserscasdfaserasdfaserqwcasrweas'
        self.assertIsNone(jobe.put_file(fileId, ('inhalt').encode()))
        self.assertTrue(jobe.check_file(fileId))


    def test_create_files_uses_opaque_jobe_ids_and_preserves_names(self):
        files = {"test.json": b"{}", "data.txt": b"hello"}

        file_specs = JobeWrapper.createFiles(files)

        self.assertEqual([spec[1] for spec in file_specs], ["test.json", "data.txt"])
        self.assertEqual([spec[2] for spec in file_specs], [b"{}", b"hello"])
        for file_id, original_name, _content in file_specs:
            self.assertNotIn(original_name, file_id)
            self.assertRegex(file_id, r"^[0-9a-f]+$")

    def test_compile_c_or_cpp_adds_stub_main_when_submission_has_no_main(self):
        jobe = JobeWrapper('jobe:80')
        with patch.object(jobe, 'run_test', return_value='result') as run_test:
            result = jobe.compile_c_or_cpp(LANGUAGE_C, 'int add(int a, int b) { return a + b; }', compileargs=['-Wall'])

        self.assertEqual(result, 'result')
        submitted_code = run_test.call_args.args[1]
        self.assertIn('int add(int a, int b)', submitted_code)
        self.assertIn('int main(void) { return 0; }', submitted_code)
        run_test.assert_called_once_with(
            LANGUAGE_C,
            submitted_code,
            'main.c',
            cputime=None,
            parameters={'compileargs': ['-Wall']},
        )

    def test_compile_c_or_cpp_keeps_existing_main(self):
        code = 'int main(void) { return 0; }'

        self.assertEqual(JobeWrapper.build_compile_probe_code(LANGUAGE_C, code), code)

    def test_run_c_uses_c_language_and_c_filename(self):
        jobe = JobeWrapper('jobe:80')
        with patch.object(jobe, 'run_test', return_value='result') as run_test:
            result = jobe.run_c('int main(void) { return 0; }')

        self.assertEqual(result, 'result')
        run_test.assert_called_once_with(
            LANGUAGE_C, 'int main(void) { return 0; }', 'main.c', None, cputime=None, parameters=None)

    def test_run_cpp_uses_cpp_language_and_cpp_filename(self):
        jobe = JobeWrapper('jobe:80')
        with patch.object(jobe, 'run_test', return_value='result') as run_test:
            result = jobe.run_cpp('int main() { return 0; }')

        self.assertEqual(result, 'result')
        run_test.assert_called_once_with(
            LANGUAGE_CPP, 'int main() { return 0; }', 'main.cpp', None, cputime=None, parameters=None)

    def test_build_catch2_program_includes_c_solution_with_c_linkage(self):
        program = JobeWrapper.build_catch2_test_program(
            LANGUAGE_C, 'answer.c', 'TEST_CASE("sum") { CHECK(add(1, 2) == 3); }')

        self.assertNotIn('#define CATCH_CONFIG_MAIN', program)
        self.assertIn('#include <catch2/catch_test_macros.hpp>', program)
        self.assertIn('extern "C" {\n#include "answer.c"\n}', program)
        self.assertIn('TEST_CASE("sum")', program)

    def test_run_catch2_tests_uploads_solution_and_uses_cpp_runner(self):
        jobe = JobeWrapper('jobe:80')
        auxiliary_file = ('input-id', 'input.txt', b'1 2')
        with patch.object(jobe, 'run_cpp', return_value='result') as run_cpp:
            result = jobe.run_catch2_tests(
                LANGUAGE_CPP,
                'int add(int left, int right) { return left + right; }',
                'TEST_CASE("sum") { CHECK(add(1, 2) == 3); }',
                [auxiliary_file],
            )

        self.assertEqual(result, 'result')
        program, files, filename = run_cpp.call_args.args
        self.assertEqual(filename, CATCH2_TEST_FILENAME)
        self.assertIn('#include "answer.cpp"', program)
        self.assertEqual(files[0][1:], ('answer.cpp', b'int add(int left, int right) { return left + right; }'))
        self.assertRegex(files[0][0], r'^[0-9a-f]+$')
        self.assertEqual(files[1], auxiliary_file)
        self.assertEqual(run_cpp.call_args.kwargs.get('compileargs'), ['-L/usr/local/lib', '-Wl,--whole-archive', '-lCatch2Main', '-lCatch2', '-Wl,--no-whole-archive'])

    def test_run_catch2_tests_preserves_compileargs_and_links_catch2_libraries(self):
        jobe = JobeWrapper('jobe:80')
        with patch.object(jobe, 'run_cpp', return_value='result') as run_cpp:
            jobe.run_catch2_tests(
                LANGUAGE_CPP,
                'int add(int left, int right) { return left + right; }',
                'TEST_CASE("sum") { CHECK(add(1, 2) == 3); }',
                compileargs=['-Wall'],
            )

        self.assertEqual(run_cpp.call_args.kwargs.get('compileargs'), ['-Wall', '-L/usr/local/lib', '-Wl,--whole-archive', '-lCatch2Main', '-lCatch2', '-Wl,--no-whole-archive'])

    def test_run_catch2_tests_rejects_unsupported_language(self):
        jobe = JobeWrapper('jobe:80')

        with self.assertRaisesRegex(ValueError, "Catch2 supports only"):
            jobe.run_catch2_tests('python3', 'print(1)', 'TEST_CASE("x") {}')

    def testWithFiles(self):
        files = {'file1': ('The first file\nLine 2').encode(),
                 'file2': ('Second file').encode()}
        code = """
print(open('file1').read())
print(open('file2').read())
"""
        fileSpec = JobeWrapper.createFiles(files)
        jobe = JobeWrapper('localhost:4000')
        result = jobe.run_test('python3', code, 'test.py', fileSpec)
        self.assertTrue(result.success())
        self.assertEqual(result.stdout, "The first file\nLine 2\nSecond file\n")

    def testExamples(self):
        for example in QuestionConfigDtoExamplesWorkingIndication():
            result = checkCode('localhost:4000', example.indication, example.validation)
            self.assertTrue(result.wasSuccessful())
