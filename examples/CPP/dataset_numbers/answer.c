#include <stdio.h>

void print_numbers(int a, int b) {
    for (long long number = a; number <= b; ++number) {
        printf("%lld\n", number);
    }
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    /* Local demonstration; check/score use the current LeTTo dataset. */
    print_numbers(3, 7);
    return 0;
}
#endif
