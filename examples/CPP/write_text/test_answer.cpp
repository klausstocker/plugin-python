#include <catch2/catch_test_macros.hpp>
#include <cstddef>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
ANSWER_LINKAGE int write_names(const char *, const char *const *, size_t);
static void write_to(const std::string& path, const std::vector<std::string>& names) {
    std::vector<const char *> pointers;
    for (const auto& name : names) pointers.push_back(name.c_str());
    REQUIRE(write_names(path.c_str(), pointers.data(), pointers.size()) == 0);
}
#else
void write_names(const std::string&, const std::vector<std::string>&);
static void write_to(const std::string& path, const std::vector<std::string>& names) {
    write_names(path, names);
}
#endif

static std::string contents(const char *path) {
    std::ifstream file(path, std::ios::binary);
    REQUIRE(file.is_open());
    return std::string(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
}
TEST_CASE("write UTF-8 names with newlines") {
    write_to("written.txt", {"Ada", "Renée"});
    REQUIRE(contents("written.txt") == "Ada\nRenée\n");
}
TEST_CASE("empty names replace existing content") {
    std::ofstream("written.txt") << "old content";
    write_to("written.txt", {});
    REQUIRE(contents("written.txt").empty());
}
TEST_CASE("new names replace existing content") {
    std::ofstream("written.txt") << "old content that is much longer";
    write_to("written.txt", {"Lin"});
    REQUIRE(contents("written.txt") == "Lin\n");
}
