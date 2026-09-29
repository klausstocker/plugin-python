# LeTTo dataset variable

Return twice the supplied number. The unit tests take their input from the
question's current LeTTo dataset.

**Required setup:** A numeric LeTTo dataset variable named `number` must exist
in the question, without a unit (for example, value `7`). Create it in LeTTo
before using **check** or **score**. Applying this example does not create the
variable. Check that it appears under **Available dataset variables**.

The plugin generates `dataset.py` for check/score. The unit tests read
`DATASET_VARIABLES["number"].value`; the student function receives that value
as an argument and does not need to import `dataset`.

- `template.py`: typed student starter used as the indication.
- `test_answer.py`: teacher validation with dataset-driven inputs.

The standalone unit test needs a generated `dataset.py`; run it through the
plugin after configuring the LeTTo variable.

See [the examples guide](../README.md) for all examples.
