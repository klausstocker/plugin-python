#include "counter.h"

// Initialize at zero, increment by one, and return the current count.
Counter::Counter() : count_(0) {}
void Counter::increment() { /* TODO */ }
int Counter::value() const { return count_; }

#ifndef LETTO_UNIT_TEST
int main() {
    Counter counter;
    counter.increment();
    return counter.value() == 1 ? 0 : 1;
}
#endif
