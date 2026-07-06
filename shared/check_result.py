import json

class CheckResult():
    __magic_string__ = '__magic_string__'
    def __init__(self, resultDict: dict):
        self.count = resultDict['count'] if 'count' in resultDict else 0
        self.failures = resultDict['failures'] if 'failures' in resultDict else []
        self.errors = resultDict['errors'] if 'errors' in resultDict else []
        self.exceptions = resultDict['exceptions'] if 'exceptions' in resultDict else []
        self.failure_count = resultDict['failure_count'] if 'failure_count' in resultDict else len(self.failures)
        self.error_count = resultDict['error_count'] if 'error_count' in resultDict else len(self.errors)
        self.exception_count = resultDict['exception_count'] if 'exception_count' in resultDict else len(self.exceptions)

    @classmethod
    def from_str(cls, text):
        magic_index = text.find(CheckResult.__magic_string__) if text else -1
        if magic_index < 0:
            return cls({
                'count': 0,
                'errors': [
                    'Could not read the unit test result from Jobe output. '
                    'Please check that the validation code defines class Checker(unittest.TestCase) '
                    'and that the submitted code can be imported as answer.py.'
                ],
            })
        resultJson = text[magic_index+len(cls.__magic_string__):]
        return cls(json.loads(resultJson))

    def wasSuccessful(self):
        return self.negCount() == 0

    def negCount(self):
        return self.failure_count + self.error_count + self.exception_count

    def status(self):
        if self.count == 0:
            return "NotScored"
        if self.negCount() == 0:
            return "OK"
        if self.negCount() < self.count:
            return "TEILWEISE_OK"
        return "FALSCH"

    def score(self):
        if self.count == 0:
            return 0.
        return max(0, self.count - self.negCount()) / self.count

    def __repr__(self):
        ret = ''
        for failure in self.failures:
            ret += f'Assertion message: {str(failure)}\n'
        for error in self.errors:
            ret += f'{str(error)}\n'
        for ex in self.exceptions:
            ret += f'{str(ex)}\n'
        failing_count = self.negCount()
        successful_count = max(0, self.count - failing_count)
        ret += f'Unit tests: {successful_count} successful, {failing_count} failing.\n'
        ret += f'Unit test score: {(self.score() * 100.):.2f} %\n'
        return ret
