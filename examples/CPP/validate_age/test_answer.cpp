#include <catch2/catch_test_macros.hpp>
#include <stdexcept>

#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
#else
#define ANSWER_LINKAGE
#endif
ANSWER_LINKAGE int validate_age(int);

TEST_CASE("nonnegative ages are unchanged") {
    REQUIRE(validate_age(18) == 18);
    REQUIRE(validate_age(0) == 0);
}
TEST_CASE("negative ages are rejected") {
#if __has_include("answer.c")
    REQUIRE(validate_age(-1) == -1);
    REQUIRE(validate_age(-20) == -1);
#else
    REQUIRE_THROWS_AS(validate_age(-1), std::invalid_argument);
    REQUIRE_THROWS_AS(validate_age(-20), std::invalid_argument);
#endif
}
