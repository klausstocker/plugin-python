import unittest
from unittest.mock import patch

from shared.check import checkCatch2Code
from shared.check_result import CheckResult
from shared.jobe_wrapper import LANGUAGE_CPP


class TestCatch2CheckCode(unittest.TestCase):
    def test_parses_catch2_failure_summary(self):
        result = CheckResult.from_catch2_output(
            "test cases: 2 | 1 passed | 1 failed\nassertions: 2 | 1 passed | 1 failed\n")

        self.assertEqual(result.count, 2)
        self.assertEqual(result.failure_count, 1)
        self.assertEqual(result.score(), 0.5)

    def test_parses_catch2_all_failing_summary(self):
        result = CheckResult.from_catch2_output("test cases: 2 | 2 failed\n")

        self.assertEqual(result.count, 2)
        self.assertEqual(result.failure_count, 2)
        self.assertEqual(result.score(), 0.0)

    @patch("shared.check.JobeWrapper")
    def test_wraps_submission_and_tests_in_catch2_runner(self, wrapper_cls):
        run_result = wrapper_cls.return_value.run_catch2_tests.return_value
        run_result.stdout = "All tests passed (2 assertions in 1 test case)\n"
        run_result.success.return_value = True

        result = checkCatch2Code(
            "jobe:80", LANGUAGE_CPP, "int add() { return 3; }", "TEST_CASE(\"add\") {}")

        wrapper_cls.return_value.run_catch2_tests.assert_called_once_with(
            LANGUAGE_CPP, "int add() { return 3; }", "TEST_CASE(\"add\") {}", files=None)
        self.assertEqual(result.count, 1)
        self.assertTrue(result.wasSuccessful())
