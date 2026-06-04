import json
import math
import re
from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class DatasetVariable:
    name: str
    value: Any = None
    unit: Optional[str] = None


def extract_dataset_variables(var_hash: Any) -> list[DatasetVariable]:
    """Extract dataset variables as compact name/value/unit triples.

    The LeTTo dataset payload represents variables as a VarHashDto-like object
    with a nested ``vars`` mapping. Each variable may contain a
    ``calcErgebnisDto`` with a human-readable ``string`` and a JSON payload.
    For numeric values with units, the JSON payload contains the numeric ``d``
    value and the unit in ``originalEinheitString`` or ``grundEinheitString``.
    """
    variables = _vars_mapping(var_hash)
    return [
        DatasetVariable(name=name, value=value, unit=unit)
        for name, variable_dto in variables.items()
        for value, unit in [_extract_variable_value_and_unit(variable_dto)]
    ]


def extract_question_dataset_variables(question: Any) -> list[DatasetVariable]:
    """Extract variables from the primary dataset-variable field of a question."""
    return extract_dataset_variables(_read_field(question, "vars"))


def dataset_variables_to_python_source(variables: list[DatasetVariable]) -> str:
    """Render dataset variables as a Python module for upload to Jobe."""
    variable_dicts = [asdict(variable) for variable in variables]
    lines = [
        '"""Generated dataset variables for the Python plugin."""',
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True)",
        "class DatasetVariable:",
        "    value: object = None",
        "    unit: object = None",
        "",
        f"_DATASET_VARIABLE_VALUES = {_python_literal(variable_dicts)}",
        "DATASET_VARIABLES = {}",
        "",
        "for _dataset_variable in _DATASET_VARIABLE_VALUES:",
        "    _dataset_value = DatasetVariable(",
        "        value=_dataset_variable['value'],",
        "        unit=_dataset_variable['unit'],",
        "    )",
        "    DATASET_VARIABLES[_dataset_variable['name']] = _dataset_value",
        "    globals()[_dataset_variable['name']] = _dataset_value",
        "",
        "del _dataset_variable, _dataset_value",
        "",
    ]
    return "\n".join(lines)


def dataset_file_from_variables(variables: list[DatasetVariable]) -> dict[str, bytes]:
    """Return a Jobe file map containing dataset.py when variables are present."""
    if not variables:
        return {}
    return {"dataset.py": dataset_variables_to_python_source(variables).encode("utf-8")}


def _vars_mapping(var_hash: Any) -> dict[str, Any]:
    if var_hash is None:
        return {}
    if isinstance(var_hash, dict):
        candidate = var_hash.get("vars")
        return candidate if isinstance(candidate, dict) else var_hash
    candidate = getattr(var_hash, "vars", None)
    return candidate if isinstance(candidate, dict) else {}


def _extract_variable_value_and_unit(variable_dto: Any) -> tuple[Any, Optional[str]]:
    calc_result = _read_field(variable_dto, "calcErgebnisDto")
    calc_json = (
        _read_field(calc_result, "json_value")
        or _read_field(calc_result, "json")
    )
    parsed_json = _parse_json_object(calc_json)
    calc_string = _read_field(calc_result, "string")

    value = _extract_value(parsed_json, calc_string)
    unit = _clean_unit(
        parsed_json.get("originalEinheitString")
        or parsed_json.get("grundEinheitString")
        or _extract_unit_from_string(calc_string)
        or _read_field(variable_dto, "ze")
    )

    return value, unit


def _extract_value(parsed_json: dict[str, Any], calc_string: Any) -> Any:
    if "d" in parsed_json:
        return _normalize_number(parsed_json["d"])

    if not isinstance(calc_string, str):
        return calc_string

    number_match = re.match(
        r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)",
        calc_string,
    )
    if number_match:
        return _normalize_number(number_match.group(1))

    return calc_string


def _extract_unit_from_string(calc_string: Any) -> Optional[str]:
    if not isinstance(calc_string, str):
        return None
    quoted_unit = re.search(r"'([^']+)'", calc_string)
    if quoted_unit:
        return quoted_unit.group(1)
    unquoted_unit = re.match(
        r"^\s*[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*([^\s]+)\s*$",
        calc_string,
    )
    if unquoted_unit:
        return unquoted_unit.group(1)
    return None


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _normalize_number(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return float(value)
    except ValueError:
        return value


def _clean_unit(unit: Any) -> Optional[str]:
    if unit is None:
        return None
    unit_text = str(unit).strip()
    if "," in unit_text:
        unit_text = unit_text.split(",", 1)[0]
    unit_text = unit_text.strip().strip("'").strip('"')
    return unit_text or None


def _read_field(value: Any, name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _python_literal(value: Any) -> str:
    if isinstance(value, float):
        if math.isnan(value):
            return "float('nan')"
        if math.isinf(value):
            return "float('inf')" if value > 0 else "float('-inf')"
        return repr(value)
    if isinstance(value, dict):
        items = ", ".join(
            f"{_python_literal(key)}: {_python_literal(item_value)}"
            for key, item_value in value.items()
        )
        return "{" + items + "}"
    if isinstance(value, list):
        return "[" + ", ".join(_python_literal(item) for item in value) + "]"
    if isinstance(value, tuple):
        items = ", ".join(_python_literal(item) for item in value)
        suffix = "," if len(value) == 1 else ""
        return "(" + items + suffix + ")"
    return repr(value)
