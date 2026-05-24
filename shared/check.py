from shared.jobe_wrapper import JobeWrapper
from shared.check_result import CheckResult
import unittest
import json

__imports__ = """
import unittest
import sys
from io import StringIO
import json

class CountingTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.assert_count = 0
        self.failed_assert_count = 0
        self.test_details = {}
        self._current_test_key = None

    def startTest(self, test):
        super().startTest(test)
        key = str(test)
        self._current_test_key = key
        self.test_details[key] = {
            'assert_count': 0,
            'failed_assert_count': 0,
            'had_error': False
        }

    def stopTest(self, test):
        super().stopTest(test)
        self._current_test_key = None

    def addError(self, test, err):
        key = str(test)
        if key in self.test_details:
            self.test_details[key]['had_error'] = True
        super().addError(test, err)


class CountingTestCase(unittest.TestCase):
    def _callTestMethod(self, method):
        def wrap_assert(fn):
            def wrapped(*args, **kwargs):
                if self._outcome and self._outcome.result:
                    self._outcome.result.assert_count += 1
                    key = self._outcome.result._current_test_key
                    if key in self._outcome.result.test_details:
                        self._outcome.result.test_details[key]['assert_count'] += 1
                try:
                    return fn(*args, **kwargs)
                except AssertionError:
                    if self._outcome and self._outcome.result:
                        self._outcome.result.failed_assert_count += 1
                        key = self._outcome.result._current_test_key
                        if key in self._outcome.result.test_details:
                            self._outcome.result.test_details[key]['failed_assert_count'] += 1
                    raise
            return wrapped

        originals = {}
        for name in dir(unittest.TestCase):
            if name.startswith('assert'):
                attr = getattr(self, name, None)
                if callable(attr):
                    originals[name] = attr
                    setattr(self, name, wrap_assert(attr))
        try:
            return super()._callTestMethod(method)
        finally:
            for name, attr in originals.items():
                setattr(self, name, attr)

"""

def checkCode(server, code, testCode):
    code2run = code + __imports__ + testCode + """
class RedirectedStdout:
    def __init__(self):
        self._stdout = None
        self._string_io = None

    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._string_io = StringIO()
        return self

    def __exit__(self, type, value, traceback):
        sys.stdout = self._stdout

    def __str__(self):
        return self._string_io.getvalue()

def main():
    unittestOutput = StringIO()
    ret = {'count' : 0, 'assert_count': 0, 'failed_assert_count': 0, 'test_details': [], 'errors': [], 'failures': [], 'exceptions': []}
    try:
        suite = unittest.TestLoader().loadTestsFromTestCase(type('CountingChecker', (CountingTestCase, Checker), {}))
        runner = unittest.TextTestRunner(verbosity=0, stream=unittestOutput, resultclass=CountingTestResult)
        result = runner.run(suite)
        ret['count'] = result.testsRun
        ret['assert_count'] = result.assert_count
        ret['failed_assert_count'] = result.failed_assert_count
        ret['test_details'] = list(result.test_details.values())
        for error in result.errors:
            ret['errors'].append(error)
        for failure in result.failures:
            ret['failures'].append(failure)
    except Exception as e:
        ret['exceptions'].append(e)
    return ret

if __name__ == '__main__':
    __magic_string__ = '__magic_string__'
    ret = main()
    print(f'{__magic_string__}{json.dumps(ret, separators=(',', ':'))}')
"""
    jobe = JobeWrapper(server)
    result = jobe.run_test('python3', code2run, 'test.py')
    if not result.success():
        return CheckResult({'count': 0, 'errors': ['error running code']})
    return CheckResult.from_str(result.stdout, (code + __imports__).count('\n'))
