"""Small examples, from printed output to LeTTo dataset variables."""

from pathlib import Path

from shared.question_config import QuestionConfigDto

_EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
EXAMPLE_NAMES = (
    "printed_output",
    "calculate_sum",
    "temperature",
    "even_numbers",
    "validate_age",
    "counter",
    "read_text",
    "write_text",
    "numpy_means",
    "sqlite_products",
    "dataset_double",
)
REFERENCE_EXAMPLE_NAMES = tuple(name for name in EXAMPLE_NAMES if name != "dataset_double")


def _example_file(example_name: str, filename: str) -> str:
    return (_EXAMPLES_DIR / example_name / filename).read_text(encoding="utf-8")


def _examples(indication_filename: str, names: tuple[str, ...] = EXAMPLE_NAMES) -> list[QuestionConfigDto]:
    return [
        QuestionConfigDto(
            indication=_example_file(name, indication_filename),
            validation=_example_file(name, "test_answer.py"),
            files={"names.txt": _example_file(name, "names.txt")} if name == "read_text" else {},
            linterConfig="--disable=C0114,C0115,C0116",
            linterWeight=0.5,
        )
        for name in names
    ]


def QuestionConfigDtoExamples() -> list[QuestionConfigDto]:
    """Examples for teachers with unfinished, typed student templates."""
    return _examples("template.py")


def QuestionConfigDtoExamplesWorkingIndication() -> list[QuestionConfigDto]:
    """Examples with standalone reference solutions for integration checks."""
    return _examples("answer.py", REFERENCE_EXAMPLE_NAMES)
