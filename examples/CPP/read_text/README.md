# read_text

Read a UTF-8 text file and return its lines without line endings, preserving
empty lines. The example supplies [names.txt](names.txt), including `Renée`.

C fills caller-provided `char output[capacity][128]` rows and returns the line
count, or `-1` on error. Each line has at most 127 UTF-8 bytes; provide enough rows.
C++ returns `std::vector<std::string>` and throws on a file read error.

- C: [template](template.c), [solution](answer.c).
- C++: [template](template.cpp), [solution](answer.cpp).
- [Catch2 tests](test_answer.cpp): supplied file, empty file, CRLF and blank lines.

See [the C/C++ examples guide](../README.md) for setup and scoring.
