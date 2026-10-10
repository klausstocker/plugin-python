# Python plugin examples

## 1. Printed output

**Feature:** Check top-level printed output by importing `answer` inside `RedirectedStdout`.

**Task:** Print `hello world` followed by a newline. 

[Possible solution](printed_output/answer.py)

## 2. Return value

**Feature:** Check a function's return value.

**Task:** Return the sum of two integers.

[Possible solution](calculate_sum/answer.py)

## 3. Floating-point result

**Feature:** Check floating-point results with a tolerance.

**Task:** Convert Celsius to Fahrenheit using celsius * 9 / 5 + 32.

[Possible solution](temperature/answer.py)

## 4. Lists

**Feature:** Check returned lists, including order and duplicates.

**Task:** Return all even numbers, preserving their order and duplicates.

[Possible solution](even_numbers/answer.py)

## 5. Exceptions

**Feature:** Check that invalid input raises an exception.

**Task:** Return the age unchanged; raise ValueError if it is negative.

[Possible solution](validate_age/answer.py)

## 6. Student class

**Feature:** Check methods and state of student-written classes.

**Task:** Implement Counter: start at zero, increment by one, and return the current value.

[Possible solution](counter/answer.py)

## 7. Read a text file

**Feature:** Provide a text file through the plugin and check its contents are read correctly.

**Task:** Read a UTF-8 text file and return its lines without line endings.

[Possible solution](read_text/answer.py)

## 8. Write a text file

**Feature:** Check text files written by the student's program.

**Task:** Write each name followed by a newline to a UTF-8 file; replace any existing content.

[Possible solution](write_text/answer.py)

## 9. NumPy

**Feature:** Use NumPy and check array results.

**Task:** Return the mean of each column of a nonempty two-dimensional NumPy array.

[Possible solution](numpy_means/answer.py)

## 10. SQLite

**Feature:** Use SQLite and check query results.

**Task:** Return product names with price strictly below max_price, ordered by name. Use the supplied connection and products(name TEXT, price REAL) table.

[Possible solution](sqlite_products/answer.py)

## 11. LeTTo dataset variable

**Feature:** Use the current LeTTo dataset as input to the unit tests.

**Required setup:** A numeric LeTTo dataset variable named `number` must exist
in the question, without a unit (for example, value `7`). Create it in LeTTo
before using **check** or **score**. Applying the example does not create it.
It must appear under **Available dataset variables** in the configuration.

**Task:** Implement `double(value)` to return twice the supplied value.
Import the runtime-provided `dataset` module to access the current LeTTo dataset.
For example, a dataset variable named `i` is available as:

```python
import dataset

value = dataset.i.value
```

In this example, the unit tests use `dataset.number.value` and pass it to the
student function.
