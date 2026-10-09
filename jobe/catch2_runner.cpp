#include <catch2/catch_session.hpp>
#include <fstream>
#include <iostream>
#include <chrono>

int main() {
    Catch::Session session;
    const char* args[] = {"catch2-tests", "--reporter", "xml", "--out", "catch2-results.xml"};
    const auto started = std::chrono::steady_clock::now();
    const int result = session.run(5, args);
    const double seconds = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - started).count();
    std::ifstream report("catch2-results.xml");
    std::cout << "\n__catch2_execution__{\"test_run_wall_seconds\":" << seconds << "}\n";
    std::cout << "\n__catch2_report__\n" << report.rdbuf();
    return result;
}
