// Required setup: Create dataset variables a and n in the LeTTo question yourself.
// Use integer values without units, with n >= 0 (for example, a = 3 and n = 4).
// Applying this example does not create them. Check/score use their current values.
// This test calculates b = a + n and passes the endpoints a and b to the student.
// This unit test is shared by the C and C++ examples.

#include <catch2/catch_test_macros.hpp>
#include "dataset.h"
#include "helpers.c"
#include <string>

#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
#else
#define ANSWER_LINKAGE
#endif
ANSWER_LINKAGE void print_numbers(int a, int b);

TEST_CASE("print a through b inclusive using the current dataset") {
    const int a = static_cast<int>(dataset_get("a")->value);
    const int b = a + static_cast<int>(dataset_get("n")->value);
    std::string actual;
    {
        CaptureStdout output;
        print_numbers(a, b);
        actual = output.text();
    }
    std::string expected;
    for (long long number = a; number <= b; ++number) {
        expected += std::to_string(number) + "\n";
    }
    REQUIRE(actual == expected);
}
