# C/C++ plugin examples

## 01 calculate_sum

**Task:** Return the sum of two integers. The tests check positive and negative values.

[Template](calculate_sum/template.cpp) · [Catch2 tests](calculate_sum/test_answer.cpp) · [Possible solution](calculate_sum/answer.cpp)

## 02 printed_output

**Task:** Print `hello world` followed by a newline. The test captures stdout from `print_message()`.

[Template](printed_output/template.cpp) · [Catch2 tests](printed_output/test_answer.cpp) · [Possible solution](printed_output/answer.cpp)

## 03 read_file

**Task:** Read the integer in `number.txt` and return it from `read_file()`.
The example supplies [number.txt](read_file/number.txt) containing `42`.

[Template](read_file/template.cpp) · [Catch2 tests](read_file/test_answer.cpp) · [Possible solution](read_file/answer.cpp)

## 04 even_numbers

**Task:** Return the even integers, preserving their order and duplicates.
C fills an output array; C++ returns a vector.

[C template](even_numbers/template.c) · [C solution](even_numbers/answer.c) · [C++ template](even_numbers/template.cpp) · [C++ solution](even_numbers/answer.cpp) · [Catch2 tests](even_numbers/test_answer.cpp)

## 05 validate_age

**Task:** Return a nonnegative age unchanged. Reject negative ages with `-1`
in C or `std::invalid_argument` in C++.

[C template](validate_age/template.c) · [C solution](validate_age/answer.c) · [C++ template](validate_age/template.cpp) · [C++ solution](validate_age/answer.cpp) · [Catch2 tests](validate_age/test_answer.cpp)

## 06 counter

**Task:** Start at zero, increment by one, and return the current value.
C implements functions for a struct; C++ implements a class.
The example supplies [counter.h](counter/counter.h).

[C template](counter/template.c) · [C solution](counter/answer.c) · [C++ template](counter/template.cpp) · [C++ solution](counter/answer.cpp) · [Catch2 tests](counter/test_answer.cpp)

## 07 read_text

**Task:** Read UTF-8 lines without line endings, preserving blank lines.
The example supplies [names.txt](read_text/names.txt).
C fills string buffers; C++ returns a vector of strings.

[C template](read_text/template.c) · [C solution](read_text/answer.c) · [C++ template](read_text/template.cpp) · [C++ solution](read_text/answer.cpp) · [Catch2 tests](read_text/test_answer.cpp)

## 08 write_text

**Task:** Write each UTF-8 name followed by a newline, replacing existing contents.
An empty list must produce an empty file.

[C template](write_text/template.c) · [C solution](write_text/answer.c) · [C++ template](write_text/template.cpp) · [C++ solution](write_text/answer.cpp) · [Catch2 tests](write_text/test_answer.cpp)

## 09 dataset_numbers

**Task:** Implement `print_numbers(a, b)` using a loop to print all integers from
`a` through `b` inclusive, one number per line, including a final newline.
The unit test calculates `b = a + n` from the dataset.

**Required setup:** Create integer LeTTo dataset variables named `a` and `n`,
without units; `n` must be nonnegative. For `a = 3`, `n = 4`, print `3`, `4`, `5`,
`6`, `7` on separate lines. Applying the example does not create the variables.

The tests read the current values through `dataset_get("a")` and
`dataset_get("n")` in the runtime-provided `dataset.h`, calculate `b = a + n`,
and call `print_numbers(a, b)`. See [the example details](dataset_numbers/README.md).

[C template](dataset_numbers/template.c) · [C solution](dataset_numbers/answer.c) · [C++ template](dataset_numbers/template.cpp) · [C++ solution](dataset_numbers/answer.cpp) · [Catch2 tests](dataset_numbers/test_answer.cpp)

## Using the examples

The UnitTest dropdown lists both C and C++ entries, with labels such as
`C 04 even_numbers` and `C++ 04 even_numbers`. Applying an example selects C17
or C++17 and loads the matching student template, Catch2 tests, and example files.
Examples 01–03 use portable `.cpp` templates and solutions for both languages.
Examples 04–09 provide separate `.c` and `.cpp` templates and solutions.
The plugin submits C answers as `answer.c` and C++ answers as `answer.cpp`;
the Catch2 tests are always compiled as C++17.

Tests select C linkage automatically when `answer.c` is present. Student functions
are compiled separately from the tests. Keep the supplied `LETTO_UNIT_TEST` guard
around `main` so the program can run manually without conflicting with Catch2's main.

Each `TEST_CASE` is one scored case. Use **check** or **score** to test a template
against its Catch2 tests, and **run** or **compile** in the Template tab to try the
student program. The unfinished templates intentionally fail the tests.
