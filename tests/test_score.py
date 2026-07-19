import sys
import types
import unittest
from unittest.mock import patch

fake_lint_module = types.ModuleType('shared.lint')
fake_lint_module.lintCode = lambda code, linter_config='': (10.0, [])
sys.modules.setdefault('shared.lint', fake_lint_module)

from shared.score import scoreCode


class FakeCheckResult:
    def __init__(self, value):
        self._value = value
        self.count = 0

    def score(self):
        return self._value

    def __repr__(self):
        return f"Score: {self._value}\n"


class TestScoreCode(unittest.TestCase):
    @patch('shared.score.checkCode')
    @patch('shared.score.lintCode')
    def test_score_without_lint_weight_uses_check_score_only(self, lint_mock, check_mock):
        check_mock.return_value = FakeCheckResult(0.6)

        score, result = scoreCode('jobe:80', 'print(1)', 'tests', '--disable=C0114', 0.0)

        self.assertEqual(score, 0.6)
        self.assertIs(result.check_result, check_mock.return_value)
        lint_mock.assert_not_called()

    @patch('shared.score.checkCode')
    @patch('shared.score.lintCode')
    def test_score_with_lint_weight_combines_scores(self, lint_mock, check_mock):
        check_mock.return_value = FakeCheckResult(0.4)
        lint_mock.return_value = (8.0, [])

        score, _ = scoreCode('jobe:80', 'print(1)', 'tests', '--disable=C0114', 2.0)

        expected = (0.4 + 2.0 * 0.8) / (1.0 + 2.0)
        self.assertAlmostEqual(score, expected)
        lint_mock.assert_called_once_with('print(1)', '--disable=C0114')

    @patch('shared.score.JobeWrapper')
    @patch('shared.score.checkCode')
    def test_c_score_with_warning_weight_counts_compiler_warnings(self, check_mock, wrapper_mock):
        check_mock.return_value = FakeCheckResult(0.5)
        run_result = wrapper_mock.return_value.run_test.return_value
        run_result.cmpinfo = "main.c:1:1: warning: first warning\nmain.c:2:1: warning: second warning"
        run_result.stderr = ""

        score, result = scoreCode('jobe:80', 'int main(void) { return 0; }', '', '-Wall -std=c99', 1.0, language='c')

        expected_warning_score = 0.8
        self.assertAlmostEqual(score, (0.5 + expected_warning_score) / 2.0)
        self.assertIn("Warning weight", result.__repr__())
        wrapper_mock.return_value.run_test.assert_called_once_with(
            'c',
            'int main(void) { return 0; }',
            'main.c',
            cputime=None,
            parameters={'compileargs': ['-Wall', '-std=c99']},
        )

    @patch('shared.score.JobeWrapper')
    @patch('shared.score.checkCode')
    def test_cpp_score_with_ten_warnings_has_zero_warning_score(self, check_mock, wrapper_mock):
        check_mock.return_value = FakeCheckResult(1.0)
        run_result = wrapper_mock.return_value.run_test.return_value
        run_result.cmpinfo = "\n".join(f"main.cpp:{i}:1: warning: warning {i}" for i in range(10))
        run_result.stderr = ""

        score, _ = scoreCode('jobe:80', 'int main() { return 0; }', '', '-Wall', 1.0, language='cpp')

        self.assertAlmostEqual(score, 0.5)


if __name__ == '__main__':
    unittest.main()


class TestScoreResult(unittest.TestCase):
    def test_check_result_repr_includes_successful_and_failing_counts(self):
        from shared.check_result import CheckResult
        r = CheckResult({
            "count": 3,
            "failures": ["helpful message"],
            "errors": ["error"],
            "exceptions": [],
            "failure_count": 1,
            "error_count": 1,
        })
        text = r.__repr__()
        self.assertIn("Unit tests: 1 successful, 2 failing.", text)
        self.assertIn("Assertion message: helpful message", text)

    def test_check_result_repr_can_count_failures_without_assertion_details(self):
        from shared.check_result import CheckResult
        r = CheckResult({"count": 2, "failures": [], "failure_count": 1, "errors": [], "exceptions": []})
        text = r.__repr__()
        self.assertIn("Unit tests: 1 successful, 1 failing.", text)
        self.assertNotIn("AssertionError", text)

    def test_check_result_from_str_reports_missing_jobe_result(self):
        from shared.check_result import CheckResult
        r = CheckResult.from_str("unexpected jobe output")
        text = r.__repr__()
        self.assertIn("Could not read the unit test result from Jobe output", text)

    def test_score_result_repr_with_lint_details(self):
        from shared.score_result import ScoreResult
        r = ScoreResult(FakeCheckResult(0.5), 0.7, 2.0)
        text = r.__repr__()
        self.assertIn("Linter weight: 2.0000", text)
        self.assertIn("Linter score: 70.00 %", text)
        self.assertIn("Overall score: 63.33 %", text)
