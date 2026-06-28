# calculate_sum example

This folder is a self-contained development workspace for a Python plugin example.

- `answer.py` contains the solution implementation.
- `test_answer.py` contains unit tests for `answer.py` using Python's built-in `unittest` framework.

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
