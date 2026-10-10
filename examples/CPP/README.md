# C/C++ plugin examples

## 01 calculate_sum

**Task:** Return the sum of two integers. The tests check positive and negative values.

[Template](calculate_sum/template.cpp) · [Catch2 tests](calculate_sum/test_answer.cpp) · [Possible solution](calculate_sum/answer.cpp)

## 02 printed_output

**Task:** Print `Hello!` followed by a newline. The test captures stdout from `print_message()`.

[Template](printed_output/template.cpp) · [Catch2 tests](printed_output/test_answer.cpp) · [Possible solution](printed_output/answer.cpp)

## 03 read_file

**Task:** Read the integer in `number.txt` and return it from `read_file()`.
The example supplies [number.txt](read_file/number.txt) containing `42`.

[Template](read_file/template.cpp) · [Catch2 tests](read_file/test_answer.cpp) · [Possible solution](read_file/answer.cpp)

## Using the examples

Select C17 or C++17 as the answer language, then apply an example in the UnitTest tab.
The `.cpp` templates and solutions contain portable code that works with either
answer language. The plugin submits C answers as `answer.c` and C++ answers as
`answer.cpp`; the Catch2 tests are always compiled as C++17.

Tests select C linkage automatically when `answer.c` is present. Student functions
are compiled separately from the tests. Keep the supplied `LETTO_UNIT_TEST` guard
around `main` so the program can run manually without conflicting with Catch2's main.

Each `TEST_CASE` is one scored case. Use **check** or **score** to test a template
against its Catch2 tests, and **run** or **compile** in the Template tab to try the
student program. The unfinished templates intentionally fail the tests.
