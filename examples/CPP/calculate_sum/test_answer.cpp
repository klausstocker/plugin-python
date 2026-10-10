#include <catch2/catch_test_macros.hpp>
// Jobe supplies answer.c for C answers and answer.cpp for C++ answers.
#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
#else
#define ANSWER_LINKAGE
#endif
ANSWER_LINKAGE int calculate_sum(int, int);
TEST_CASE("sum") {
    REQUIRE(calculate_sum(2, 3) == 5);
}
TEST_CASE("negative") {
    REQUIRE(calculate_sum(-2, 1) == -1);
}
