import json

class CheckResult():
    __magic_string__ = '__magic_string__'
    def __init__(self, resultDict: dict, offset=0):
        self._offset = offset
        self.count = resultDict['count'] if 'count' in resultDict else 0
        self.failures = resultDict['failures'] if 'failures' in resultDict else []
        self.errors = resultDict['errors'] if 'errors' in resultDict else []
        self.exceptions = resultDict['exceptions'] if 'exceptions' in resultDict else []

    @classmethod
    def from_str(res, text, offset=0):
        resultJson = text[text.find(CheckResult.__magic_string__)+len(CheckResult.__magic_string__):]
        return CheckResult(json.loads(resultJson), offset)

    def wasSuccessful(self):
        return self.negCount() == 0

    def negCount(self):
        return len(self.failures) + len(self.errors) + len(self.exceptions)

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
            ret += f'{str(failure)}\n'
        for error in self.errors:
            ret += f'{str(error)}\n'
        for ex in self.exceptions:
            ret += f'{str(ex)}\n'
        ret += f'Ran {self.count} Test, {len(self.failures)} failures, {len(self.errors)} errors, {len(self.exceptions)} exceptions\n'
        ret += f'Score: {(self.score() * 100.):.2f} %\n'
        return ret
