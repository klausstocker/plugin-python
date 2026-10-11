#include <stddef.h>

/* Write even values to output, preserving order and duplicates.
 * output has space for count integers. Return the number written. */
size_t even_numbers(const int *values, size_t count, int *output) {
    (void)values;
    (void)count;
    (void)output;
    return 0; /* TODO */
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    const int values[] = {3, 2, -4, 2, 0};
    int output[5];
    return even_numbers(values, 5, output) == 4 ? 0 : 1;
}
#endif
