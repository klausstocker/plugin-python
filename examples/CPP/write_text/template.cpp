#include <string>
#include <vector>

// Replace the file with each UTF-8 name followed by a newline. Throw on errors.
void write_names(const std::string& path, const std::vector<std::string>& names) {
    (void)path;
    (void)names; // TODO
}

#ifndef LETTO_UNIT_TEST
int main() { write_names("written.txt", {"Ada", "Renée"}); }
#endif
