#include <catch2/catch_test_macros.hpp>
// Jobe supplies answer.c for C answers and answer.cpp for C++ answers.
#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
#else
#define ANSWER_LINKAGE
#endif
ANSWER_LINKAGE int read_file(void);
TEST_CASE("number from file") {
    REQUIRE(read_file() == 42);
}
