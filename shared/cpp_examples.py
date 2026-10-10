"""Independent C/C++ examples for the Cpp plugin."""
from shared.question_config import CppQuestionConfigDto


def cpp_examples(language='cpp'):
    if language not in {'c', 'cpp'}:
        raise ValueError('Language must be c or cpp')
    common = '''#include <catch2/catch_test_macros.hpp>
// Jobe supplies answer.c for C answers and answer.cpp for C++ answers.
#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
#else
#define ANSWER_LINKAGE
#endif
'''
    stdout_test = common + '''#include <cstdio>
#include <string>
#include <unistd.h>
ANSWER_LINKAGE void print_message(void);
TEST_CASE("printed message") {
    FILE* captured = tmpfile();
    REQUIRE(captured != nullptr);
    fflush(stdout);
    int saved = dup(fileno(stdout));
    REQUIRE(saved >= 0);
    REQUIRE(dup2(fileno(captured), fileno(stdout)) >= 0);
    print_message();
    fflush(stdout);
    dup2(saved, fileno(stdout));
    close(saved);
    rewind(captured);
    char buffer[128] = {};
    size_t length = fread(buffer, 1, sizeof(buffer), captured);
    fclose(captured);
    REQUIRE(std::string(buffer, length) == "Hello!\\n");
}
'''
    entries = [
        ("Function test", 'int calculate_sum(int a, int b) { return 0; }\n'
         '\n#ifndef LETTO_UNIT_TEST\n#include <stdio.h>\n'
         'int main(void) { printf("Sum: %d\\n", calculate_sum(2, 3)); return 0; }\n#endif\n',
         common + 'ANSWER_LINKAGE int calculate_sum(int, int);\n'
         'TEST_CASE("sum") { REQUIRE(calculate_sum(2, 3) == 5); }\n'
         'TEST_CASE("negative") { REQUIRE(calculate_sum(-2, 1) == -1); }\n', {}),
        ("stdout", '#include <stdio.h>\nvoid print_message(void) { /* print Hello! */ }\n'
         '\n#ifndef LETTO_UNIT_TEST\n'
         'int main(void) { print_message(); return 0; }\n#endif\n', stdout_test, {}),
        ("Read a file", '#include <stdio.h>\nint read_number(void) { return 0; }\n'
         '\n#ifndef LETTO_UNIT_TEST\n'
         'int main(void) { printf("Number: %d\\n", read_number()); return 0; }\n#endif\n',
         common + 'ANSWER_LINKAGE int read_number(void);\n'
         'TEST_CASE("number from file") { REQUIRE(read_number() == 42); }\n', {'number.txt': '42\n'}),
    ]
    return [dict(CppQuestionConfigDto(language=language, indication=answer,
                                     validation=tests, files=files).model_dump(), title=title)
            for title, answer, tests, files in entries]
