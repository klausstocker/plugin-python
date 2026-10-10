#include <stddef.h>

size_t even_numbers(const int *values, size_t count, int *output) {
    size_t written = 0;
    for (size_t i = 0; i < count; ++i) {
        if (values[i] % 2 == 0) output[written++] = values[i];
    }
    return written;
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    const int values[] = {3, 2, -4, 2, 0};
    int output[5];
    return even_numbers(values, 5, output) == 4 ? 0 : 1;
}
#endif
