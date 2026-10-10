"""Real compiler checks; run inside the Catch2-enabled Jobe image."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(shutil.which('gcc') and Path('/opt/catch2/lib/libCatch2.a').exists(),
                     'Requires the Catch2-enabled Jobe image')
class TestCppEntrypoint(unittest.TestCase):
    def test_student_main_runs_manually_and_is_excluded_from_catch2(self):
        script = Path(__file__).resolve().parents[1] / 'jobe' / 'catch2_compile.py'
        for language, compiler, standard in [('c', 'gcc', '-std=c17'), ('cpp', 'g++', '-std=c++17')]:
            with self.subTest(language=language), tempfile.TemporaryDirectory() as directory:
                workspace = Path(directory)
                answer = 'answer.c' if language == 'c' else 'answer.cpp'
                (workspace / answer).write_text(
                    'int answer(void) { return 42; }\n'
                    '#ifndef LETTO_UNIT_TEST\n'
                    '#include <stdio.h>\n'
                    'int main(void) { puts("Student main"); return answer() == 42 ? 0 : 1; }\n'
                    '#endif\n')
                linkage = 'extern "C" ' if language == 'c' else ''
                (workspace / 'test.cpp').write_text(
                    '#include <catch2/catch_test_macros.hpp>\n'
                    '#ifndef LETTO_UNIT_TEST\n#error Missing test macro\n#endif\n'
                    + linkage + 'int answer(void);\n'
                    'TEST_CASE("student function") { REQUIRE(answer() == 42); }\n')

                def run(command):
                    result = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    return result.stdout

                run([compiler, standard, '-Wall', '-Werror', answer, '-o', 'student'])
                self.assertIn('Student main', run(['./student']))
                for phase in ('prepare', 'finish'):
                    run([sys.executable, str(script), language, 'test.cpp', 'tests', phase])
                report = run(['./tests'])
                self.assertIn('__catch2_report__', report)
                self.assertIn('student function', report)
                self.assertNotIn('Student main', report)
