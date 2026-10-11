"""Integration tests requiring Jobe at localhost:4000 (same as test_jobe)."""

import json
import unittest
from unittest.mock import patch

from shared.jobe_wrapper import JobeWrapper, RunResult


class TestJobeLanguages(unittest.TestCase):
    def test_languages_requests_json(self):
        jobe = JobeWrapper('localhost:4000')
        with patch.object(jobe, 'do_http', return_value=[['c', '13.3.0'], ['cpp', '13.3.0']]) as request:
            self.assertEqual(jobe.languages(), {'c': '13.3.0', 'cpp': '13.3.0'})
        request.assert_called_once_with(
            'GET', '/jobe/index.php/restapi/languages', {'Accept': 'application/json'})


class TestJobeCompiledLanguages(unittest.TestCase):
    languages = (('c', 'test.c'), ('cpp', 'test.cpp'))

    def setUp(self):
        self.jobe = JobeWrapper('localhost:4000')

    def test_supported_languages_have_compiler_versions(self):
        versions = self.jobe.languages()
        for language, _ in self.languages:
            with self.subTest(language=language):
                self.assertIn(language, versions)
                self.assertRegex(versions[language], r'\d+\.\d+')

    def test_run_and_stdout(self):
        programs = {
            'c': '#include <stdio.h>\nint main(void) { puts("Hello C!"); return 0; }',
            'cpp': '#include <iostream>\nint main() { std::cout << "Hello C++!\\n"; return 0; }',
        }
        for language, filename in self.languages:
            with self.subTest(language=language):
                result = self.jobe.run_test(language, programs[language], filename)
                self.assertTrue(result.success(), repr(result))
                self.assertEqual(result.stdout, 'Hello C!\n' if language == 'c' else 'Hello C++!\n')
                self.assertFalse(result.stderr)

    def test_compile_error(self):
        for language, filename in self.languages:
            with self.subTest(language=language):
                result = self.jobe.run_test(language, 'int main(void) { return missing_symbol; }', filename)
                self.assertFalse(result.success())
                self.assertEqual(result.outcome()[0], 11, repr(result))
                self.assertIn('missing_symbol', result.cmpinfo)

    def test_runtime_error(self):
        for language, filename in self.languages:
            with self.subTest(language=language):
                result = self.jobe.run_test(
                    language, '#include <stdlib.h>\nint main(void) { abort(); }', filename)
                self.assertFalse(result.success())
                self.assertEqual(result.outcome()[0], 12, repr(result))

    def test_configured_cpu_limit(self):
        code = '''
#include <stdio.h>
#include <time.h>
int main(void) {
    clock_t start = clock();
    while ((double)(clock() - start) / CLOCKS_PER_SEC < 2.0) { }
    puts("finished cpu work");
    return 0;
}
'''
        for language, filename in self.languages:
            with self.subTest(language=language):
                short = self.jobe.run_test(language, code, filename, cputime=1)
                self.assertEqual(short.outcome()[0], 13, repr(short))
                long = self.jobe.run_test(language, code, filename, cputime=5)
                self.assertTrue(long.success(), repr(long))
                self.assertEqual(long.stdout, 'finished cpu work\n')

    def test_uploaded_file_can_be_read_and_written(self):
        code = '''
#include <stdio.h>
int main(void) {
    char text[64];
    FILE *input = fopen("input.txt", "r");
    if (!input || !fgets(text, sizeof(text), input)) return 1;
    fclose(input);
    FILE *output = fopen("output.txt", "w");
    if (!output) return 2;
    if (fputs(text, output) == EOF) return 3;
    if (fclose(output) != 0) return 4;
    output = fopen("output.txt", "r");
    if (!output || !fgets(text, sizeof(text), output)) return 5;
    fclose(output);
    fputs(text, stdout);
    return 0;
}
'''
        for language, filename in self.languages:
            with self.subTest(language=language):
                files = JobeWrapper.createFiles({'input.txt': b'Hello file!\n'})
                result = self.jobe.run_test(language, code, filename, files=files)
                self.assertTrue(result.success(), repr(result))
                self.assertEqual(result.stdout, 'Hello file!\n')

    def test_uploaded_header_is_available_during_compilation(self):
        code = '#include <stdio.h>\n#include "answer.h"\nint main(void) { printf("%d\\n", answer()); return 0; }'
        for language, filename in self.languages:
            with self.subTest(language=language):
                files = JobeWrapper.createFiles({'answer.h': b'int answer(void) { return 42; }'})
                result = self.jobe.run_test(language, code, filename, files=files)
                self.assertTrue(result.success(), repr(result))
                self.assertEqual(result.stdout, '42\n')

    def test_additional_source_and_explicit_language_standard(self):
        # Probe Jobe's REST parameters before adding compiler options to our wrapper.
        for language, filename in self.languages:
            with self.subTest(language=language):
                suffix = 'c' if language == 'c' else 'cpp'
                standard = '-std=c17' if language == 'c' else '-std=c++17'
                support_name = 'answer.' + suffix
                file_id, _, content = JobeWrapper.createFiles({
                    support_name: b'int answer(void) { return 42; }',
                })[0]
                self.assertIsNone(self.jobe.put_file(file_id, content))
                self.assertTrue(self.jobe.check_file(file_id))
                payload = {'run_spec': {
                    'language_id': language,
                    'sourcefilename': filename,
                    'sourcecode': '#include <stdio.h>\nint answer(void);\nint main(void) { printf("%d\\n", answer()); return 0; }',
                    'file_list': [(file_id, support_name)],
                    'parameters': {
                        'compileargs': ['-Wall', '-Werror', standard],
                        'linkargs': [support_name],
                    },
                }}
                result = RunResult(self.jobe.do_http(
                    'POST', '/jobe/index.php/restapi/runs',
                    {'Content-type': 'application/json', 'Accept': 'application/json'},
                    json.dumps(payload)))
                self.assertTrue(result.success(), repr(result))
                self.assertEqual(result.stdout, '42\n')
