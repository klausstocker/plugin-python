"""SQL teaching examples shared by the configuration dialog and tests."""
from shared.package_data import data_path

from shared.question_config import SqlQuestionConfigDto


EXAMPLES_DIR = data_path('examples/SQL')
EXAMPLE_NAMES = ('select_products', 'insert_products', 'update_prices', 'delete_products', 'join_products')


def sql_example(index: int, *, solution: bool = False) -> SqlQuestionConfigDto:
    if type(index) is not int or not 0 <= index < len(EXAMPLE_NAMES):
        raise ValueError('Invalid SQL example index')
    folder = EXAMPLES_DIR / EXAMPLE_NAMES[index]
    return SqlQuestionConfigDto(
        preparation=(folder / 'preparation.sql').read_text(encoding='utf-8'),
        indication=(folder / ('solution.sql' if solution else 'template.sql')).read_text(encoding='utf-8'),
        validation=(folder / 'test_answer.py').read_text(encoding='utf-8'))
