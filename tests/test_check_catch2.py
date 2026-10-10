import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from shared.check_catch2 import check_catch2, parse_catch2_report
from shared.jobe_wrapper import JobeWrapper, RunResult


class TestCatch2Reports(unittest.TestCase):
    def test_test_cases_determine_score_not_assertions(self):
        report = '''__catch2_report__
<Catch2TestRun><TestCase name="wrong sum"><OverallResult success="false"/></TestCase>
<OverallResults successes="20" failures="3"/>
<OverallResultsCases successes="1" failures="1"/></Catch2TestRun>'''
        result = parse_catch2_report(report)
        self.assertEqual(result.count, 2)
        self.assertEqual(result.failure_count, 1)
        self.assertEqual(result.score(), 0.5)
        self.assertEqual(result.failures, ['wrong sum'])

    def test_invalid_or_empty_reports_are_errors(self):
        for report in ('', '__catch2_report__\n<broken',
                       '__catch2_report__\n<Catch2TestRun/>',
                       '__catch2_report__\n<Catch2TestRun><OverallResultsCases successes="0" failures="0"/></Catch2TestRun>'):
            with self.subTest(report=report):
                result = parse_catch2_report(report)
                self.assertFalse(result.wasSuccessful())
                self.assertEqual(result.count, 0)
                self.assertTrue(result.errors)


class TestCatch2Submissions(unittest.TestCase):
    @patch('shared.check_catch2.JobeWrapper')
    def test_invalid_language_is_rejected_before_submission(self, wrapper):
        with self.assertRaises(ValueError):
            check_catch2('unused', '', '', language='python')
        wrapper.assert_not_called()

    def test_reserved_uploads_cannot_replace_submission_files(self):
        files = JobeWrapper.createFiles({
            name: b'stale' for name in (
                'answer.c', 'answer.cpp', 'answer.o', 'test.cpp', 'test.cpp.exe',
                'catch2-tests.o', 'catch2-results.xml', 'helpers.c', 'input.txt')
        })
        report = ('__catch2_report__\n<Catch2TestRun>'
                  '<OverallResultsCases successes="1" failures="0"/></Catch2TestRun>')
        for language, filename in (('c', 'answer.c'), ('cpp', 'answer.cpp')):
            with self.subTest(language=language), patch.object(
                    JobeWrapper, 'run_test', return_value=RunResult({'outcome': 15, 'stdout': report})) as run:
                result = check_catch2('unused', 'student code', 'teacher tests',
                                      language=language, files=files, cputime=9)
                self.assertTrue(result.wasSuccessful())
                self.assertEqual(result.count, 1)
                args = run.call_args
                self.assertEqual(args.args, ('catch2' + language, 'teacher tests', 'test.cpp'))
                self.assertEqual(args.kwargs['cputime'], 9)
                uploaded = {name: content for _, name, content in args.kwargs['files']}
                self.assertEqual(uploaded[filename], b'student code')
                self.assertEqual(uploaded['input.txt'], b'stale')
                self.assertEqual(set(uploaded), {filename, 'input.txt', 'helpers.h', 'helpers.c', 'dataset.h'})
                self.assertNotEqual(uploaded['helpers.c'], b'stale')

    def test_jobe_failure_becomes_a_check_error(self):
        for outcome in (11, 12, 13, 99):
            with self.subTest(outcome=outcome), patch.object(
                    JobeWrapper, 'run_test', return_value=RunResult({'outcome': outcome, 'stderr': 'diagnostic'})):
                result = check_catch2('unused', '', '')
                self.assertEqual(result.count, 0)
                self.assertFalse(result.wasSuccessful())
                self.assertIn('diagnostic', result.errors[0])


class TestCatch2Jobe(unittest.TestCase):
    """Uses the project's Jobe service at localhost:4000."""

    server = os.environ.get('JOBE_TEST_SERVER', 'localhost:4000')

    def test_cache_reuses_test_object_for_changed_answers_and_invalidates_headers(self):
        test_source = ('#include <catch2/catch_test_macros.hpp>\n#include "expected.h"\n'
                       'int answer();\nTEST_CASE("' + uuid.uuid4().hex + '") { REQUIRE(answer() == EXPECTED); }')

        def run(answer, expected):
            result = JobeWrapper(self.server).run_test(
                'catch2cpp', test_source, 'test.cpp', files=JobeWrapper.createFiles({
                    'answer.cpp': answer.encode(),
                    'expected.h': f'#define EXPECTED {expected}\n'.encode(),
                }))
            self.assertTrue(result.success(), repr(result))
            self.assertTrue(parse_catch2_report(result.stdout).wasSuccessful())
            return result.timings

        first = run('int answer() { return 42; }', 42)
        second = run('int answer() { return 40 + 2; }', 42)
        changed_header = run('int answer() { return 43; }', 43)
        self.assertFalse(first['test_cache_hit'])
        self.assertTrue(second['test_cache_hit'])
        self.assertEqual(second['test_compile_wall_seconds'], 0)
        self.assertGreater(second['answer_compile_wall_seconds'], 0)
        self.assertGreater(second['link_wall_seconds'], 0)
        self.assertFalse(changed_header['test_cache_hit'])

    def test_included_answer_changes_invalidate_test_object(self):
        tests = ('#include <catch2/catch_test_macros.hpp>\n#include "answer.cpp"\n'
                 'TEST_CASE("' + uuid.uuid4().hex + '") { REQUIRE(value == 42); }')
        # constexpr definitions are local to each translation unit.
        for answer in (b'constexpr int value = 42;', b'constexpr int value = 40 + 2;'):
            result = JobeWrapper(self.server).run_test(
                'catch2cpp', tests, 'test.cpp',
                files=JobeWrapper.createFiles({'answer.cpp': answer}))
            self.assertTrue(result.success(), repr(result))
            self.assertTrue(parse_catch2_report(result.stdout).wasSuccessful())
            self.assertFalse(result.timings['test_cache_hit'])

    def test_time_macros_disable_test_object_cache(self):
        tests = ('#include <catch2/catch_test_macros.hpp>\n'
                 'TEST_CASE("' + uuid.uuid4().hex + '") { REQUIRE(sizeof(__TIME__) > 1); }')
        for _ in range(2):
            result = JobeWrapper(self.server).run_test(
                'catch2cpp', tests, 'test.cpp',
                files=JobeWrapper.createFiles({'answer.cpp': b'int answer() { return 42; }'}))
            self.assertTrue(result.success(), repr(result))
            self.assertFalse(result.timings['test_cache_hit'])

    def test_concurrent_submissions_share_first_compilation(self):
        tests = ('#include <catch2/catch_test_macros.hpp>\nint answer();\n'
                 'TEST_CASE("' + uuid.uuid4().hex + '") { REQUIRE(answer() == 42); }')

        def run(_):
            return JobeWrapper(self.server).run_test(
                'catch2cpp', tests, 'test.cpp',
                files=JobeWrapper.createFiles({'answer.cpp': b'int answer() { return 42; }'}))

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(run, range(2)))
        for result in results:
            self.assertTrue(result.success(), repr(result))
            self.assertTrue(parse_catch2_report(result.stdout).wasSuccessful())
        self.assertEqual(sorted(result.timings['test_cache_hit'] for result in results), [False, True])

    def test_cached_link_failure_retries_with_fresh_test_object(self):
        tests = ('#include <catch2/catch_test_macros.hpp>\nint answer();\n'
                 'TEST_CASE("' + uuid.uuid4().hex + '") { REQUIRE(answer() == 42); }')
        first = JobeWrapper(self.server).run_test(
            'catch2cpp', tests, 'test.cpp',
            files=JobeWrapper.createFiles({'answer.cpp': b'int answer() { return 42; }'}))
        self.assertTrue(first.success(), repr(first))
        result = JobeWrapper(self.server).run_test(
            'catch2cpp', tests, 'test.cpp',
            files=JobeWrapper.createFiles({'answer.cpp': b'int other() { return 42; }'}))
        self.assertEqual(result.outcome()[0], 11, repr(result))
        self.assertFalse(result.timings['test_cache_hit'])
        self.assertGreater(result.timings['test_cache_retry_wall_seconds'], 0)
        self.assertGreater(result.timings['test_compile_wall_seconds'], 0)

    def test_answer_filename_presence_invalidates_has_include(self):
        tests = ('#include <catch2/catch_test_macros.hpp>\nextern "C" int answer();\n'
                 '#if __has_include("answer.c")\n#define EXPECTED 42\n#else\n#define EXPECTED 43\n#endif\n'
                 'TEST_CASE("' + uuid.uuid4().hex + '") { REQUIRE(answer() == EXPECTED); }')
        for language, name, answer in (
                ('catch2c', 'answer.c', b'int answer() { return 42; }'),
                ('catch2cpp', 'answer.cpp', b'extern "C" int answer() { return 43; }')):
            result = JobeWrapper(self.server).run_test(
                language, tests, 'test.cpp', files=JobeWrapper.createFiles({name: answer}))
            self.assertTrue(result.success(), repr(result))
            self.assertTrue(parse_catch2_report(result.stdout).wasSuccessful())
            self.assertFalse(result.timings['test_cache_hit'])

    def test_catch2_version(self):
        versions = JobeWrapper(self.server).languages()
        self.assertEqual(versions['catch2c'], '3.16.0')
        self.assertEqual(versions['catch2cpp'], '3.16.0')

    def test_phase_timings_and_client_round_trip(self):
        result = JobeWrapper(self.server).run_test(
            'catch2cpp', '#include <catch2/catch_test_macros.hpp>\n'
            'int answer();\nTEST_CASE("answer") { REQUIRE(answer() == 42); }', 'test.cpp',
            files=JobeWrapper.createFiles({'answer.cpp': b'int answer() { return 42; }'}))
        self.assertTrue(result.success(), repr(result))
        self.assertTrue(parse_catch2_report(result.stdout).wasSuccessful())
        for phase in ('answer_compile', 'test_compile', 'link'):
            self.assertGreaterEqual(result.timings[phase + '_wall_seconds'], 0)
            self.assertGreaterEqual(result.timings[phase + '_cpu_seconds'], 0)
        self.assertGreaterEqual(result.timings['total_client_seconds'], result.timings['run_request_seconds'])
        self.assertGreaterEqual(result.timings['compile_sandbox_wall_seconds'],
                                sum(result.timings[phase + '_wall_seconds']
                                    for phase in ('answer_compile', 'test_compile', 'link')))
        self.assertGreaterEqual(result.timings['execute_sandbox_wall_seconds'],
                                result.timings['test_run_wall_seconds'])

    def check(self, language, answer, tests, **kwargs):
        if language == 'c':
            declarations = 'extern "C" { int calculate_sum(int, int); }'
        else:
            declarations = 'int calculate_sum(int, int);'
        return check_catch2(self.server, answer,
                            '#include <catch2/catch_test_macros.hpp>\n' + declarations + '\n' + tests,
                            language=language, **kwargs)

    def test_functions_pass(self):
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                # Designated initializers verify that C really is compiled as C17.
                answer = ('int calculate_sum(int a, int b) { struct Pair { int x; int y; }; '
                          'struct Pair p = {.y = b, .x = a}; return p.x + p.y; }') if language == 'c' else (
                          '#include <numeric>\n#include <array>\n'
                          'int calculate_sum(int a, int b) { std::array<int, 2> p{a,b}; '
                          'return std::accumulate(p.begin(), p.end(), 0); }')
                result = self.check(language, answer,
                    'TEST_CASE("sum") { REQUIRE(calculate_sum(2, 3) == 5); }\n'
                    'TEST_CASE("negative") { REQUIRE(calculate_sum(-2, 1) == -1); }')
                self.assertTrue(result.wasSuccessful(), repr(result))
                self.assertEqual(result.count, 2)

    def test_one_passing_one_failing(self):
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                result = self.check(language, 'int calculate_sum(int a, int b) { return a + b; }',
                    'TEST_CASE("pass") { REQUIRE(calculate_sum(2, 3) == 5); }\n'
                    'TEST_CASE("fail") { REQUIRE(calculate_sum(2, 3) == 6); }')
                self.assertEqual(result.count, 2, repr(result))
                self.assertEqual(result.failure_count, 1)
                self.assertEqual(result.score(), 0.5)
                self.assertIn('fail', result.failures)

    def test_compile_and_link_errors(self):
        for language in ('c', 'cpp'):
            for answer in ('int calculate_sum(int a, int b) { return missing_symbol; }',
                           'int other_function(void) { return 0; }'):
                with self.subTest(language=language, answer=answer):
                    result = self.check(language, answer,
                        'TEST_CASE("sum") { REQUIRE(calculate_sum(2, 3) == 5); }')
                    self.assertEqual(result.count, 0)
                    self.assertFalse(result.wasSuccessful())
                    self.assertIn('Compile error', result.errors[0])

    def test_uploaded_file_and_student_stdout(self):
        answer = '''#include <stdio.h>
int calculate_sum(int a, int b) {
    FILE *input = fopen("number.txt", "r");
    int value = 0;
    if (!input || fscanf(input, "%d", &value) != 1) return -1;
    fclose(input);
    puts("student stdout before report");
    return a + b + value;
}'''
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                result = self.check(language, answer,
                    'TEST_CASE("file") { REQUIRE(calculate_sum(2, 3) == 12); }',
                    files=JobeWrapper.createFiles({'number.txt': b'7'}))
                self.assertEqual(result.count, 1, repr(result))
                self.assertTrue(result.wasSuccessful(), repr(result))

    def test_cpu_timeout(self):
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                result = self.check(language,
                    'int calculate_sum(int a, int b) { for (;;) {} }',
                    'TEST_CASE("timeout") { REQUIRE(calculate_sum(2, 3) == 5); }',
                    cputime=1)
                self.assertFalse(result.wasSuccessful())
                self.assertEqual(result.count, 0)
                self.assertIn('Time limit exceeded', result.errors[0])

    def test_invalid_validation_and_empty_suite(self):
        for tests in ('TEST_CASE("broken") { REQUIRE(missing_symbol == 1); }', ''):
            with self.subTest(tests=tests):
                result = self.check('cpp', 'int calculate_sum(int a, int b) { return a + b; }', tests)
                self.assertFalse(result.wasSuccessful(), repr(result))
                self.assertEqual(result.count, 0)
                self.assertTrue(result.errors)

    def test_runtime_abort(self):
        for language in ('c', 'cpp'):
            with self.subTest(language=language):
                result = self.check(language,
                    '#include <stdlib.h>\nint calculate_sum(int a, int b) { abort(); }',
                    'TEST_CASE("abort") { REQUIRE(calculate_sum(2, 3) == 5); }')
                self.assertFalse(result.wasSuccessful())
                self.assertEqual(result.count, 0)
                self.assertIn('Runtime error', result.errors[0])
