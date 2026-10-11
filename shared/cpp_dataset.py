"""Generate student-specific C/C++ dataset headers for Jobe submissions."""
import math
import struct
from pathlib import Path

from app.dataset_helper import DatasetVariable, dataset_variables_from_payload


def _string_literal(value: str) -> str:
    # Fixed-width octal escapes preserve UTF-8 bytes without consuming a
    # following digit, and cannot inject source code into either language.
    if '\0' in value:
        raise ValueError('C/C++ dataset names and units cannot contain NUL')
    escaped = ''.join(
        chr(byte) if 32 <= byte < 127 and byte not in (34, 63, 92)
        else f'\\{byte:03o}'
        for byte in value.encode('utf-8'))
    return '"' + escaped + '"'


def _float_literal(variable: DatasetVariable) -> str | None:
    """Return a C float literal, or None for nonnumeric LeTTo variables."""
    try:
        value = float(variable.value)
    except (ValueError, TypeError):
        return None
    except OverflowError as error:
        raise ValueError(f'Dataset variable {variable.name!r} exceeds the float range') from error
    if math.isnan(value):
        return 'NAN'
    if math.isinf(value):
        return 'INFINITY' if value > 0 else '-INFINITY'
    if abs(value) > 3.4028234663852886e38:
        raise ValueError(f'Dataset variable {variable.name!r} exceeds the float range')
    # Round to the requested float type before emitting the literal, including
    # underflow to signed zero, so tiny values do not trigger compiler warnings.
    value = struct.unpack('f', struct.pack('f', value))[0]
    return repr(value) + 'f'


def cpp_helper_files(language: str = 'cpp') -> dict[str, bytes]:
    """Supply the support types independently of student-specific datasets."""
    if language not in {'c', 'cpp'}:
        raise ValueError('Dataset language must be c or cpp')
    helper_path = Path(__file__).resolve().parents[1] / 'resources/plugins/Cpp/helpers.h'
    return {'helpers.h': helper_path.read_bytes()}


def cpp_dataset_files(variables: list[DatasetVariable], language: str = 'cpp') -> dict[str, bytes]:
    """Supply teacher-test helpers.h, helpers.c, and a student-specific dataset.h."""
    files = cpp_helper_files(language)
    helper_path = Path(__file__).resolve().parents[1] / 'resources/plugins/Cpp/helpers.c'
    files['helpers.c'] = helper_path.read_bytes()
    # Match Python's name-keyed mapping when a payload repeats a name.
    values = {variable.name: variable for variable in variables}
    entries = []
    for name, variable in values.items():
        literal = _float_literal(variable)
        if literal is None:
            continue
        entries.append((_string_literal(name), literal, _string_literal(variable.unit or '')))
    lines = ['// Generated for this submission; do not edit.',
             '// Only numeric LeTTo dataset variables are exported.', '#pragma once',
             '#include "helpers.h"', '#include <math.h>',
             '#include <stddef.h>', '#include <string.h>',
             'static const dataset_entry DATASET_VARIABLES[] = {']
    lines += [f'    {{{name}, {{{value}, {unit}}}}},' for name, value, unit in entries]
    # The sentinel keeps an empty dataset valid ISO C, without zero-size arrays.
    lines += ['    {NULL, {0.0f, ""}}', '};',
              f'static const size_t DATASET_VARIABLE_COUNT = {len(entries)};',
              'static inline const variable *dataset_get(const char *name) {',
              '    if (name == NULL) return NULL;',
              '    for (size_t i = 0; i != DATASET_VARIABLE_COUNT; ++i) {',
              '        if (strcmp(DATASET_VARIABLES[i].name, name) == 0)',
              '            return &DATASET_VARIABLES[i].data;',
              '    }', '    return NULL;', '}']
    lines += ['']
    files['dataset.h'] = '\n'.join(lines).encode('utf-8')
    return files


def cpp_dataset_files_from_payload(payload, language='cpp'):
    return cpp_dataset_files(dataset_variables_from_payload(payload), language)
