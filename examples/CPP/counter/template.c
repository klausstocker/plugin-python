#include "counter.h"

/* Initialize at zero, increment by one, and return the current count. */
void counter_init(Counter *counter) { counter->count = 0; }
void counter_increment(Counter *counter) { (void)counter; /* TODO */ }
int counter_value(const Counter *counter) { return counter->count; }

#ifndef LETTO_UNIT_TEST
int main(void) {
    Counter counter;
    counter_init(&counter);
    counter_increment(&counter);
    return counter_value(&counter) == 1 ? 0 : 1;
}
#endif
