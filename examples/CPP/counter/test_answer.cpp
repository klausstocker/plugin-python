#include <catch2/catch_test_macros.hpp>
#if __has_include("answer.c")
#define LETTO_COUNTER_C
#endif
#include "counter.h"

// Wrap the C functions so both languages run the same behavior checks.
#if __has_include("answer.c")
class StudentCounter {
    Counter counter_;
public:
    StudentCounter() { counter_init(&counter_); }
    void increment() { counter_increment(&counter_); }
    int value() const { return counter_value(&counter_); }
};
#else
using StudentCounter = Counter;
#endif

TEST_CASE("initial value is zero") {
    StudentCounter counter;
    REQUIRE(counter.value() == 0);
}
TEST_CASE("increment changes the count") {
    StudentCounter counter;
    counter.increment();
    counter.increment();
    REQUIRE(counter.value() == 2);
}
TEST_CASE("instances have independent state") {
    StudentCounter first;
    StudentCounter second;
    first.increment();
    REQUIRE(first.value() == 1);
    REQUIRE(second.value() == 0);
}
