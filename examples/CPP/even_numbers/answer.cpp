#include <vector>

std::vector<int> even_numbers(const std::vector<int>& values) {
    std::vector<int> output;
    for (int value : values) {
        if (value % 2 == 0) output.push_back(value);
    }
    return output;
}

#ifndef LETTO_UNIT_TEST
int main() {
    return even_numbers({3, 2, -4, 2, 0}).size() == 4 ? 0 : 1;
}
#endif
