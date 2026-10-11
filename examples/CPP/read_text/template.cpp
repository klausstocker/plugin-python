#include <string>
#include <vector>

// Read UTF-8 lines without CR/LF endings. Throw on a file read error.
std::vector<std::string> read_lines(const std::string& path) {
    (void)path;
    return {}; // TODO
}

#ifndef LETTO_UNIT_TEST
int main() { return read_lines("names.txt").size() == 3 ? 0 : 1; }
#endif
