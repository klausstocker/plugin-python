"""Load portable C/C++ templates and Catch2 tests from the examples folders."""
from pathlib import Path

from shared.question_config import CppQuestionConfigDto

_EXAMPLES_DIR = Path(__file__).resolve().parents[1] / 'examples' / 'CPP'
EXAMPLE_NAMES = ('calculate_sum', 'printed_output', 'read_file')
_SOURCE_FILES = {'template.cpp', 'test_answer.cpp', 'answer.cpp', 'README.md'}


def cpp_examples(language='cpp'):
    if language not in {'c', 'cpp'}:
        raise ValueError('Language must be c or cpp')
    entries = []
    for name in EXAMPLE_NAMES:
        directory = _EXAMPLES_DIR / name
        config = CppQuestionConfigDto(
            language=language,
            indication=(directory / 'template.cpp').read_text(encoding='utf-8'),
            validation=(directory / 'test_answer.cpp').read_text(encoding='utf-8'),
            files={path.name: path.read_text(encoding='utf-8')
                   for path in sorted(directory.iterdir())
                   if path.is_file() and path.name not in _SOURCE_FILES},
        )
        entries.append(dict(config.model_dump(), title=directory.name))
    return entries
