# dataset_numbers

Implement `print_numbers(int a, int b)` with a loop. Print every integer from
`a` through `b`, including both endpoints, one number per line with a
newline after the last number. The unit test calculates `b = a + n` from the
dataset. For dataset `a = 3`, `n = 4`, it calls `print_numbers(3, 7)` and expects
`3`, `4`, `5`, `6`, `7` on separate lines. For `n = 0`, `b = a`, so print only `a`.

Create LeTTo dataset variables named `a` and `n` in the question, without units.
The values `a`, `n`, and `a + n` must fit in `int`; `n` must be nonnegative. Use small values
such as `a = 3`, `n = 4`. They must appear under **Available dataset variables**.
Applying the example does not create the variables.

The teacher tests include the runtime-provided `dataset.h`, read
`dataset_get("a")->value` and `dataset_get("n")->value`, calculate `b = a + n`,
and pass the endpoints `a` and `b` to the student function.
They capture stdout and compare every output line.
The plugin also supplies `helpers.c`; including it provides `StdoutBuffer` and
`CaptureStdout` for capturing both `printf` and `std::cout` output.
For local teacher tests, download [helpers.c](../../../resources/plugins/Cpp/helpers.c)
and put it alongside the test source.
The dataset header stores numeric values as floats; choose integers that are
represented exactly (small classroom examples are sufficient).
Neither `dataset.h` nor saved dataset values are bundled with the example.

The guarded `main` runs a local demonstration with endpoints `3, 7`. **check** and **score**
use the current LeTTo dataset. The answer function itself needs no dataset header.
The solutions use a `long long` loop counter so incrementing past `b` is safe.

- C: [template](template.c), [solution](answer.c).
- C++: [template](template.cpp), [solution](answer.cpp).
- [Catch2 test](test_answer.cpp): exact printed output using the current `a` and `n`.

See [the C/C++ examples guide](../README.md) for setup and scoring.
