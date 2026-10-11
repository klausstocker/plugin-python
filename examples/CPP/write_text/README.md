# write_text

Write each UTF-8 name followed by a newline, replacing existing file contents.
An empty list must create or truncate the file to zero bytes.

C uses `write_names(path, names, count)` and returns `0` on success or `-1` on
a file error. C++ uses `write_names(path, std::vector<std::string>)` and throws
on file errors.

- C: [template](template.c), [solution](answer.c).
- C++: [template](template.cpp), [solution](answer.cpp).
- [Catch2 tests](test_answer.cpp): exact UTF-8 output and replacement of old content.

See [the C/C++ examples guide](../README.md) for setup and scoring.
