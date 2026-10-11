# dataset_numbers

Implement `print_numbers(a, b)` with a loop. Print every integer from `a`
through `b`, including both endpoints, with one number per line and a
newline after the last number. The unit test calculates `b = a + n` from the
dataset. For dataset `a = 3`, `n = 4`, it calls `print_numbers(3, 7)` and expects
`3`, `4`, `5`, `6`, `7` on separate lines. For `n = 0`, `b = a`, so print only `a`.

Create LeTTo dataset variables named `a` and `n` in the question, without units.
Both must be integers; `n` must be nonnegative. Start with small values,
such as `a = 3`, `n = 4`. They must appear under **Available dataset variables**.
Applying the example does not create the variables.

The teacher tests import the runtime-provided `dataset` module, read
`dataset.a.value` and `dataset.n.value`, calculate `b = a + n`, and pass the
endpoints `a` and `b` to the student function.
`RedirectedStdout` captures its output for an exact comparison.
The student function uses its arguments, so it works with every current dataset.
Neither `dataset.py` nor saved dataset values are bundled with the example.

- [Student template](template.py)
- [Possible solution](answer.py)
- [Teacher tests](test_answer.py)

See [the examples guide](../README.md) for all examples.
