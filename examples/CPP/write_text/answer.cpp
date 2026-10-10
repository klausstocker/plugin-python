#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

void write_names(const std::string& path, const std::vector<std::string>& names) {
    std::ofstream file(path);
    if (!file) throw std::runtime_error("Cannot open file");
    for (const auto& name : names) file << name << '\n';
    file.close();
    if (!file) throw std::runtime_error("Cannot write file");
}

#ifndef LETTO_UNIT_TEST
int main() { write_names("written.txt", {"Ada", "Renée"}); }
#endif
