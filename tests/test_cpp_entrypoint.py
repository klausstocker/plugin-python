"""Entrypoint checks through the project's Jobe service at localhost:4000."""
import os
import unittest

from shared.check_catch2 import parse_catch2_report
from shared.jobe_wrapper import JobeWrapper


class TestCppEntrypoint(unittest.TestCase):
    def test_student_main_runs_manually_and_is_excluded_from_catch2(self):
        jobe = JobeWrapper(os.environ.get('JOBE_TEST_SERVER', 'localhost:4000'))
        answer_source = (
            'int answer(void) { return 42; }\n'
            '#ifndef LETTO_UNIT_TEST\n'
            '#include <stdio.h>\n'
            'int main(void) { puts("Student main"); return answer() == 42 ? 0 : 1; }\n'
            '#endif\n'
        )
        for language, standard in (('c', '-std=c17'), ('cpp', '-std=c++17')):
            with self.subTest(language=language):
                answer = 'answer.c' if language == 'c' else 'answer.cpp'
                manual = jobe.run_test(language, answer_source, answer,
                                       parameters={'compileargs': [standard, '-Wall', '-Werror']})
                self.assertTrue(manual.success(), repr(manual))
                self.assertEqual(manual.stdout, 'Student main\n')

                linkage = 'extern "C" ' if language == 'c' else ''
                test_source = (
                    '#include <catch2/catch_test_macros.hpp>\n'
                    '#ifndef LETTO_UNIT_TEST\n#error Missing test macro\n#endif\n'
                    + linkage + 'int answer(void);\n'
                    'TEST_CASE("student function") { REQUIRE(answer() == 42); }\n')

                checked = jobe.run_test(
                    'catch2' + language, test_source, 'test.cpp',
                    files=JobeWrapper.createFiles({answer: answer_source.encode()}))
                self.assertTrue(checked.success(), repr(checked))
                report = parse_catch2_report(checked.stdout)
                self.assertTrue(report.wasSuccessful(), repr(report))
                self.assertEqual(report.count, 1)
                self.assertIn('student function', checked.stdout)
                self.assertNotIn('Student main', checked.stdout)
