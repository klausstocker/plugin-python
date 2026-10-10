#include <stdio.h>
void print_message(void) { /* print Hello! */
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    print_message();
    return 0;
}
#endif
