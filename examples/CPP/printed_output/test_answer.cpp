#include <catch2/catch_test_macros.hpp>
// Jobe supplies answer.c for C answers and answer.cpp for C++ answers.
#if __has_include("answer.c")
#define ANSWER_LINKAGE extern "C"
#else
#define ANSWER_LINKAGE
#endif
#include <cstdio>
#include <string>
#include <unistd.h>
ANSWER_LINKAGE void print_message(void);
TEST_CASE("printed message") {
    FILE *captured = tmpfile();
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
    REQUIRE(std::string(buffer, length) == "Hello!\n");
}
