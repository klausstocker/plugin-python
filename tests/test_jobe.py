import unittest
import sys
from unittest.mock import patch

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
def correctImplementation(arg1, arg2):
    sum = arg1 + arg2
    print(f'the sum is {sum}')
    return sum

class Checker(unittest.TestCase): # do not rename
    def test_return(self): # names must start with 'test_'
        args = (1, 2)
        student_result = calculate_sum(*args) # call to students implementation
        expected_result = correctImplementation(*args)
        self.assertEqual(student_result, expected_result)

    def test_output(self):
        args = (3, 4)
        with RedirectedStdout() as student_out:
            calculate_sum(*args)
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
class Checker(unittest.TestCase): # do not rename
    def test_true(self):
        self.assertTrue(always_true())

    def test_false(self):
        self.assertFalse(always_true())
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

            result = checkCode("jobe:80", "print(open('input.txt').read())\n", "", files=files)

            wrapper.run_test.assert_called_once()
            self.assertIs(wrapper.run_test.call_args.args[3], files)
            self.assertTrue(result.wasSuccessful())

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
            result = checkCode('localhost:4000', example.indication, example.validation)
            self.assertTrue(result.wasSuccessful())
