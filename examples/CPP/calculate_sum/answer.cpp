int calculate_sum(int a, int b) {
    return a + b;
}

#ifndef LETTO_UNIT_TEST
#include <stdio.h>
int main(void) {
    printf("Sum: %d\n", calculate_sum(2, 3));
    return 0;
}
#endif
