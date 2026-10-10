#include <stdio.h>
void print_message(void) {
    puts("Hello!");
}

#ifndef LETTO_UNIT_TEST
int main(void) {
    print_message();
    return 0;
}
#endif
