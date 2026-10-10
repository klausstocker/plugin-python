#include <vector>

// Return the even values, preserving order and duplicates.
std::vector<int> even_numbers(const std::vector<int>& values) {
    (void)values;
    return {}; // TODO
}

#ifndef LETTO_UNIT_TEST
int main() {
    return even_numbers({3, 2, -4, 2, 0}).size() == 4 ? 0 : 1;
}
#endif
