from shared.jobe_wrapper import JobeWrapper
from shared.check_result import CheckResult
import uuid

ANSWER_FILENAME = "answer.py"

def _student_answer_file(code: str):
    return [(uuid.uuid4().hex, ANSWER_FILENAME, code.encode("utf-8"))]


def _with_student_answer_file(code: str, files=None):
    auxiliary_files = list(files or [])
    auxiliary_files = [file_spec for file_spec in auxiliary_files if file_spec[1] != ANSWER_FILENAME]
    return _student_answer_file(code) + auxiliary_files


def checkCode(server, code, testCode, files=None):
    code2run = testCode + """
import sys
from io import StringIO
import json

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
    ret = {'count' : 0, 'errors': [], 'failures': [], 'exceptions': [], 'failure_count': 0, 'error_count': 0}

    def custom_assertion_message(traceback_text):
        lines = [line.strip() for line in str(traceback_text).splitlines() if line.strip()]
        message = lines[-1] if lines else ''
        if message.startswith('AssertionError:'):
            message = message[len('AssertionError:'):].strip()
        if ' : ' in message:
            return message.rsplit(' : ', 1)[1].strip()
        default_assertion_fragments = [
            ' != ',
            ' == ',
            ' not ',
            ' is not ',
            ' not found in ',
            ' unexpectedly found in ',
            'Regex didn\\'t match',
            'Exception not raised',
        ]
        if any(fragment in message for fragment in default_assertion_fragments):
            return ''
        return message

    try:
        suite = unittest.TestLoader().loadTestsFromTestCase(Checker)
        runner = unittest.TextTestRunner(verbosity=0, stream=unittestOutput)
        result = runner.run(suite)
        ret['count'] = result.testsRun
        ret['failure_count'] = len(result.failures)
        ret['error_count'] = len(result.errors)
        for error in result.errors:
            ret['errors'].append(error[1] if isinstance(error, tuple) else str(error))
        for failure in result.failures:
            if isinstance(failure, tuple) and len(failure) > 1:
                failure_message = custom_assertion_message(failure[1])
                if failure_message:
                    ret['failures'].append(failure_message)
    except Exception as e:
        ret['exceptions'].append(str(e))
    return ret

if __name__ == '__main__':
    __magic_string__ = '__magic_string__'
    ret = main()
    print(f'{__magic_string__}{json.dumps(ret, separators=(',', ':'))}')
"""
    jobe = JobeWrapper(server)
    result = jobe.run_test('python3', code2run, 'test.py', _with_student_answer_file(code, files))
    if not result.success():
        return CheckResult({
            'count': 0,
            'errors': [
                'Error running Jobe unit tests. '
                f'{result.__repr__().strip()} '
                'Please check the validation tests, imports, uploaded files, and the submitted Python syntax.'
            ],
        })
    return CheckResult.from_str(result.stdout)
