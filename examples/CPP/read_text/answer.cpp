#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

std::vector<std::string> read_lines(const std::string& path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("Cannot open file");
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(file, line)) {
        if (!line.empty() && line.back() == '\r') line.pop_back();
        lines.push_back(line);
    }
    if (file.bad()) throw std::runtime_error("Cannot read file");
    return lines;
}

#ifndef LETTO_UNIT_TEST
int main() { return read_lines("names.txt").size() == 3 ? 0 : 1; }
#endif
