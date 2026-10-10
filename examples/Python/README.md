# Python plugin examples

## 1. Printed output

**Feature:** Check top-level printed output by importing `answer` inside `RedirectedStdout`.

**Task:** Print `hello world` followed by a newline. 

[Possible solution](printed_output/answer.py)

## 2. Return value

**Feature:** Check a function's return value.

**Task:** Return the sum of two integers.

[Possible solution](calculate_sum/answer.py)

## 3. Lists

**Feature:** Check returned lists, including order and duplicates.

**Task:** Return all even numbers, preserving their order and duplicates.

[Possible solution](even_numbers/answer.py)

## 4. Exceptions

**Feature:** Check that invalid input raises an exception.

**Task:** Return the age unchanged; raise ValueError if it is negative.

[Possible solution](validate_age/answer.py)

## 5. Student class

**Feature:** Check methods and state of student-written classes.

**Task:** Implement Counter: start at zero, increment by one, and return the current value.

[Possible solution](counter/answer.py)

## 6. Read a text file

**Feature:** Provide a text file through the plugin and check its contents are read correctly.

**Task:** Read a UTF-8 text file and return its lines without line endings.

[Possible solution](read_text/answer.py)

## 7. Write a text file

**Feature:** Check text files written by the student's program.

**Task:** Write each name followed by a newline to a UTF-8 file; replace any existing content.

[Possible solution](write_text/answer.py)

## 8. NumPy

**Feature:** Use NumPy and check array results.

**Task:** Return the mean of each column of a nonempty two-dimensional NumPy array.

[Possible solution](numpy_means/answer.py)

## 9. SQLite

**Feature:** Use SQLite and check query results.

**Task:** Return product names with price strictly below max_price, ordered by name. Use the supplied connection and products(name TEXT, price REAL) table.

[Possible solution](sqlite_products/answer.py)

## 10. LeTTo dataset loop

**Feature:** Read the current LeTTo dataset in the teacher tests and capture printed output.

**Required setup:** Create integer LeTTo dataset variables named `a` and `n`,
without units; `n` must be nonnegative. For example, use `a = 3`, `n = 4`.
Both must appear under **Available dataset variables**. Applying the example
does not create them.

**Task:** Implement `print_numbers(a, b)` using a loop. Print each integer from
`a` through `b` inclusive, one per line. The unit test calculates `b = a + n`
from the dataset, so print `n + 1` lines.
For `a = 3`, `n = 4`, the output is:

```text
3
4
5
6
7
```

The teacher tests read `dataset.a.value` and `dataset.n.value` from the
runtime-provided `dataset` module, calculate `b = a + n`, and pass the endpoints
`a` and `b` to the student function.
See [the example details](dataset_numbers/README.md).

[Possible solution](dataset_numbers/answer.py)
