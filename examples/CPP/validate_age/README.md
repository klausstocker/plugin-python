# validate_age

Return nonnegative ages unchanged. Reject negative ages with `-1` in C,
or by throwing `std::invalid_argument` in C++.

- C: [template](template.c), [solution](answer.c).
- C++: [template](template.cpp), [solution](answer.cpp).
- [Catch2 tests](test_answer.cpp): positive, zero, and negative ages.

See [the C/C++ examples guide](../README.md) for setup and scoring.
