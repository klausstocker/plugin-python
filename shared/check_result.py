import json

class CheckResult():
    __magic_string__ = '__magic_string__'
    def __init__(self, resultDict: dict, offset=0):
        self._offset = offset
        self.count = resultDict['count'] if 'count' in resultDict else 0
        self.failures = resultDict['failures'] if 'failures' in resultDict else []
        self.assert_count = resultDict['assert_count'] if 'assert_count' in resultDict else 0
        self.failed_assert_count = resultDict['failed_assert_count'] if 'failed_assert_count' in resultDict else len(self.failures)
        self.test_details = resultDict['test_details'] if 'test_details' in resultDict else []
        self.errors = resultDict['errors'] if 'errors' in resultDict else []
        self.exceptions = resultDict['exceptions'] if 'exceptions' in resultDict else []

    @classmethod
    def from_str(res, text, offset=0):
        resultJson = text[text.find(CheckResult.__magic_string__)+len(CheckResult.__magic_string__):]
        return CheckResult(json.loads(resultJson), offset)

    def wasSuccessful(self):
        return self.negCount() == 0

    def negCount(self):
        return self.failed_assert_count

    def status(self):
        if self.count == 0:
            return "NotScored"
        if self.negCount() == 0:
            return "OK"
        if self.negCount() < self.count:
            return "TEILWEISE_OK"
        return "FALSCH"

    def score(self):
        if len(self.test_details) > 0:
            test_scores = []
            for test_detail in self.test_details:
                if test_detail.get('had_error', False):
                    test_scores.append(0.0)
                    continue

                assert_count = test_detail.get('assert_count', 0)
                failed_assert_count = test_detail.get('failed_assert_count', 0)
                if assert_count == 0:
                    test_scores.append(1.0)
                    continue
                test_scores.append(max(0, assert_count - failed_assert_count) / assert_count)
            return sum(test_scores) / len(test_scores)

        if self.assert_count == 0:
            return 0.
        return max(0, self.assert_count - self.negCount()) / self.assert_count

    def __repr__(self):
        ret = ''
        for failure in self.failures:
            ret += f'{str(failure)}\n'
        for error in self.errors:
            ret += f'{str(error)}\n'
        for ex in self.exceptions:
            ret += f'{str(ex)}\n'
        ret += f'Ran {self.count} tests, {self.assert_count} asserts, {len(self.failures)} failures, {len(self.errors)} errors, {len(self.exceptions)} exceptions.\n'
        ret += f'Unit test score: {(self.score() * 100.):.2f} %\n'
        return ret
