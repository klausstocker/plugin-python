# counter

Initialize a counter at zero, increment by one, and read its current value.
Each instance keeps its own state.

C uses a `Counter` struct with `counter_init`, `counter_increment`, and
`counter_value`. C++ implements the `Counter` class declared in
[counter.h](counter.h), with `increment()` and `value()` methods.
The plugin supplies this header as an example file; implement the functions
and methods in the student answer.

- C: [template](template.c), [solution](answer.c).
- C++: [template](template.cpp), [solution](answer.cpp).
- [Catch2 tests](test_answer.cpp): initial value, increments, independent instances.

See [the C/C++ examples guide](../README.md) for setup and scoring.
