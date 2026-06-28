# Question creator examples

This directory contains Python plugin examples and tools for turning them into
LeTTo import files.

Each importable example lives in its own subdirectory and must provide:

- `answer.py` with the reference or starter implementation.
- `test_answer.py` with the `unittest` validation code.
- `README.md` with the question text.

## Build a LeTTo import file

To convert one specific example, pass that example folder. This is also the mode
used when you drag and drop an example folder onto the script:

```bash
python question_creator/examples_to_lto.py question_creator/calculate_sum
```

The command writes `question_creator/calculate_sum.lto` with exactly one LeTTo
question.

To convert all example subdirectories, run the script without arguments from the
repository root:

```bash
python question_creator/examples_to_lto.py
```

That command scans the example subdirectories and writes
`question_creator/examples.lto`. To write somewhere else, pass `--output`:

```bash
python question_creator/examples_to_lto.py question_creator/calculate_sum --output /tmp/calculate_sum.lto
```

The resulting `.lto` file can be imported into LeTTo.
