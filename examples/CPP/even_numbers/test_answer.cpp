#include <catch2/catch_test_macros.hpp>
#include <cstddef>
#include <vector>

#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
ANSWER_LINKAGE size_t even_numbers(const int *, size_t, int *);
static std::vector<int> filtered(const std::vector<int>& values) {
    std::vector<int> output(values.size());
    size_t count = even_numbers(values.data(), values.size(), output.data());
    REQUIRE(count <= output.size());
    output.resize(count);
    return output;
}
#else
#define ANSWER_LINKAGE
std::vector<int> even_numbers(const std::vector<int>&);
static std::vector<int> filtered(const std::vector<int>& values) {
    return even_numbers(values);
}
#endif

TEST_CASE("mixed values retain order and duplicates") {
    const std::vector<int> expected = {2, -4, 2, 0};
    REQUIRE(filtered({3, 2, -4, 2, 0}) == expected);
}
TEST_CASE("empty input") { REQUIRE(filtered({}).empty()); }
TEST_CASE("no even values") { REQUIRE(filtered({1, 3}).empty()); }
