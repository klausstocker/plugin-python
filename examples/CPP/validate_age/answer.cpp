#include <stdexcept>

int validate_age(int age) {
    if (age < 0) throw std::invalid_argument("Age must not be negative");
    return age;
}

#ifndef LETTO_UNIT_TEST
int main() { return validate_age(18) == 18 ? 0 : 1; }
#endif
