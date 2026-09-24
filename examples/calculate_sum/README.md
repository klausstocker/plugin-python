# calculate_sum example

This folder is a development workspace for a Python plugin example.

- `answer.py` contains the solution implementation.
- `test_answer.py` contains unit tests for `answer.py` using Python's built-in `unittest` framework.
- `../../shared/helpers.py` provides `RedirectedStdout` to capture printed output.
  Local tests use this shared source directly. The test runner automatically
  uploads it to Jobe for every unit-test submission; it is not part of the
  question-specific files and teachers do not need to upload it.
  The Docker image build copies the shared source to
  `/app/resources/plugins/Python/helpers.py` alongside the plugin scripts and
  help page, making it available for teachers to download. When using this
  example outside the repository, save the downloaded `helpers.py` beside
  `test_answer.py`.

## Run the tests

From this directory:

```bash
python -m unittest test_answer.py
```

From the repository root:

```bash
python -m unittest discover -s examples/calculate_sum -p "test_*.py"
```

## Visual Studio Code

Use the Python extension's **Testing** view and configure unittest discovery with:

- Framework: `unittest`
- Start directory: `examples/calculate_sum`
- Pattern: `test_*.py`
