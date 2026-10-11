# Printed output

Print `hello world` followed by a newline with a single top-level statement:

```python
print("hello world")
```

Import `answer` inside the `RedirectedStdout` block to capture the output produced
when the module executes. Compare the exact text, including the space and trailing
newline. Do not import `answer` beforehand: Python caches imports, so importing it
again would not execute the print statement.

- `template.py`: student instructions used as the indication.
- `answer.py`: working reference solution.
- `test_answer.py`: teacher validation.

The online plugin supplies `helpers.py` automatically.

For local testing, add the shared helper directory to Python's import path.
From this directory in PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path ../../shared).Path
python -m unittest test_answer.py
```

Or in Bash:

```bash
PYTHONPATH=../../shared python -m unittest test_answer.py
```

See [the examples guide](../README.md) for all examples.
