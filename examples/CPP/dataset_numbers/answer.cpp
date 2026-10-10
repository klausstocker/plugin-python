#include <iostream>

void print_numbers(int a, int b) {
    for (long long number = a; number <= b; ++number) {
        std::cout << number << '\n';
    }
}

#ifndef LETTO_UNIT_TEST
int main() {
    // Local demonstration; check/score use the current LeTTo dataset.
    print_numbers(3, 7);
}
#endif
