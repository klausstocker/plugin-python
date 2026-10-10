#include <catch2/catch_test_macros.hpp>
#include <cstddef>
#include <fstream>
#include <string>
#include <vector>

#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
ANSWER_LINKAGE int read_lines(const char *, char (*)[128], size_t);
static std::vector<std::string> lines_from(const std::string& path) {
    char lines[16][128] = {};
    int count = read_lines(path.c_str(), lines, 16);
    REQUIRE(count >= 0);
    REQUIRE(count <= 16);
    std::vector<std::string> result;
    for (int i = 0; i < count; ++i) result.emplace_back(lines[i]);
    return result;
}
#else
std::vector<std::string> read_lines(const std::string&);
static std::vector<std::string> lines_from(const std::string& path) { return read_lines(path); }
#endif

TEST_CASE("supplied UTF-8 file") {
    const std::vector<std::string> expected = {"Ada", "Renée", "Lin"};
    REQUIRE(lines_from("names.txt") == expected);
}
TEST_CASE("empty file") {
    std::ofstream("empty.txt").close();
    REQUIRE(lines_from("empty.txt").empty());
}
TEST_CASE("CRLF, blank line, and final line without newline") {
    std::ofstream("lines.txt", std::ios::binary) << "Ada\r\n\r\nLin";
    const std::vector<std::string> expected = {"Ada", "", "Lin"};
    REQUIRE(lines_from("lines.txt") == expected);
}
