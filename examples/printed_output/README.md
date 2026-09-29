# Printed output

Implement `greet(name)` so it prints `Hello, <name>!` followed by a newline.

RedirectedStdout captures print output. Compare the exact text, including spaces and the trailing newline.

- `template.py`: typed student starter used as the indication.
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
