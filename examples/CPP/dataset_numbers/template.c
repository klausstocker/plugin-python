#include <stdio.h>

/* Use a loop to print a through b inclusive, one integer per line.
 * The tests read LeTTo dataset variables a and n, calculate b = a + n,
 * and pass the endpoints a and b, with b >= a. */
void print_numbers(int a, int b) {
    (void)a;
    (void)b; /* TODO */
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    /* Local demonstration; check/score use the current LeTTo dataset. */
    print_numbers(3, 7);
    return 0;
}
#endif
