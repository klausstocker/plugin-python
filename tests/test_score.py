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


if __name__ == '__main__':
    unittest.main()


class TestScoreResult(unittest.TestCase):
    def test_score_result_repr_with_lint_details(self):
        from shared.score_result import ScoreResult
        r = ScoreResult(FakeCheckResult(0.5), 0.7, 2.0)
        text = r.__repr__()
        self.assertIn("Linter weight: 2.0000", text)
        self.assertIn("Linter score: 70.00 %", text)
        self.assertIn("Overall score: 63.33 %", text)
