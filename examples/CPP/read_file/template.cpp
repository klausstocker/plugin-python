#include <stdio.h>
int read_file(void) {
    return 0;
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    printf("Number: %d\n", read_file());
    return 0;
}
#endif
