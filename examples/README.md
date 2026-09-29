# Python plugin examples

These ten examples follow the order of the example selector, from basic output
checks to SQLite. Each introduces one main testing technique.

## Using an example

Load an example in the configuration editor. The indication contains a typed
student template with `NotImplementedError` placeholders; students implement it.
The validation imports the submission as `answer` and runs a `Checker` class.
Keep that class name and prefix test methods with `test_`.
Type hints describe the interface; tests check behavior rather than enforcing hints.

Each directory contains `template.py`, a working `answer.py`, `test_answer.py`,
and a short README. The file-reading example also supplies `names.txt` through
the question's Files configuration. The reference solutions are for teachers.
Checking an unfinished template is expected to fail.

The plugin automatically supplies `helpers.py` for validation. For downloaded
standalone tests, save [helpers.py](/images/plugins/Python/helpers.py) alongside
the checker. The repository's printed-output checker also finds the shared helper.

## Run locally

Install the project dependencies:

```sh
python -m pip install -r requirements.txt
```

Run a reference solution's checker from its own directory, for example:

```sh
cd examples/read_text
python -m unittest test_answer.py
```

Use separate processes for examples because every solution is imported as
`answer`. From the repository root, verify all examples through the plugin's
submission packaging without a Jobe server:

```sh
python -m unittest discover -s tests -p test_question_examples.py
```

All text files use UTF-8 and text mode. Tests use fixed inputs, literal expected
results, and temporary files where needed. Assertion messages can give students
specific feedback. Linter weighting stays at zero so these examples focus on
functional checks.

## Examples

### 1. Printed output

**Task:** Implement `greet(name)` so it prints `Hello, <name>!` followed by a newline.

RedirectedStdout captures print output. Compare the exact text, including spaces and the trailing newline.

Source directory: `examples/printed_output/`.

### 2. Return value

**Task:** Return the sum of two integers.

Call the student function through answer and compare its return value with assertEqual.

Source directory: `examples/calculate_sum/`.

### 3. Floating-point result

**Task:** Convert Celsius to Fahrenheit using celsius * 9 / 5 + 32.

Use assertAlmostEqual for floating-point calculations to allow small rounding differences.

Source directory: `examples/temperature/`.

### 4. Lists

**Task:** Return all even numbers, preserving their order and duplicates.

Compare lists directly. Cover empty input, duplicates, negative numbers, and ordering.

Source directory: `examples/even_numbers/`.

### 5. Exceptions

**Task:** Return the age unchanged; raise ValueError if it is negative.

Use assertRaises as a context manager to check the exception type without requiring a particular message.

Source directory: `examples/validate_age/`.

### 6. Student class

**Task:** Implement Counter: start at zero, increment by one, and return the current value.

The indication supplies the class and method signatures. Tests construct objects, call methods, and check that instances have independent state.

Source directory: `examples/counter/`.

### 7. Read a text file

**Task:** Read a UTF-8 text file and return its lines without line endings.

names.txt is supplied through QuestionConfigDto.files. An additional temporary fixture checks an empty file. All file access uses text mode and UTF-8.

Source directory: `examples/read_text/`.

### 8. Write a text file

**Task:** Write each name followed by a newline to a UTF-8 file; replace any existing content.

Give the student function a temporary output path and inspect its contents. TemporaryDirectory cleans up after each test, including failures.

Source directory: `examples/write_text/`.

### 9. NumPy

**Task:** Return the mean of each column of a nonempty two-dimensional NumPy array.

Use NumPy arrays and numpy.testing.assert_allclose. Check the shape separately so broadcasting cannot hide an incorrect result shape. NumPy must be installed locally; the Jobe image already includes it.

Source directory: `examples/numpy_means/`.

### 10. SQLite

**Task:** Return product names with price strictly below max_price, ordered by name. Use the supplied connection and products(name TEXT, price REAL) table.

Each test gets a fresh in-memory SQLite database. The reference solution binds the price as a SQL parameter and explicitly sorts results. No database file or server is needed.

Source directory: `examples/sqlite_products/`.

## Build the HTML guide

The Docker build runs `scripts/build_examples_docs.py` after copying the examples
and resources. It renders this Markdown and includes the actual templates,
checkers, fixtures, and reference solutions, so the HTML is self-contained.

To generate the same page locally from the repository root:

```sh
python scripts/build_examples_docs.py
```

The output is `resources/plugins/Python/examples.html`. The existing resource
synchronization publishes it to `/images/plugins/Python/examples.html`, linked
from the plugin help. Regenerate it after changing examples; do not edit the
generated HTML directly.
