# minimum_bmi example

This folder is a self-contained development workspace for a Python plugin example.

The task is to write a function that receives a list of tuples in the form
`(name, weight, height)` and returns the name of the person with the minimum BMI.
BMI is calculated as `weight / height**2`.

- `answer.py` contains an example list of tuples and the solution implementation.
- `test_answer.py` contains unit tests for `answer.py` using Python's built-in `unittest` framework.
- The tests intentionally use a different list of tuples than the example data in `answer.py`.

## Run the tests

From this directory:

```bash
python -m unittest test_answer.py
```

From the repository root:

```bash
python -m unittest discover -s examples/minimum_bmi -p "test_*.py"
```

## Visual Studio Code

Use the Python extension's **Testing** view and configure unittest discovery with:

- Framework: `unittest`
- Start directory: `examples/minimum_bmi`
- Pattern: `test_*.py`
