import unittest
import sys
from unittest.mock import patch

from app.dataset_helper import DatasetVariable, dataset_file_from_variables
from shared.jobe_wrapper import JobeWrapper
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
        create_files = JobeWrapper.createFiles

        class FakeRunResult:
            stdout = '__magic_string__{"count":1,"errors":[],"failures":[],"exceptions":[]}'

            def success(self):
                return True

        with patch("shared.check.JobeWrapper") as wrapper_cls:
            wrapper_cls.createFiles.side_effect = create_files
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
            self.assertEqual(submitted_files[1:-1], files)
            self.assertEqual(submitted_files[-1][1], "helpers.py")
            self.assertIn(b"class RedirectedStdout:", submitted_files[-1][2])
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
            jobe.run_test('python3', 'print(1)', 'test.py', cputime=12)

        payload = do_http.call_args.args[3]
        self.assertIn('"cputime":12', payload)

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
            file_data = {
                name: content.encode("utf-8") for name, content in example.files.items()
            }
            file_data.update(dataset_file_from_variables([
                DatasetVariable(name="number", value=7),
            ]))
            files = JobeWrapper.createFiles(file_data)
            result = checkCode('localhost:4000', example.indication, example.validation, files=files)
            self.assertTrue(result.wasSuccessful())
