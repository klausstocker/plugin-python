"""Build Python wrappers without interpolating SQL into executable Python."""
from pathlib import Path

from shared.check import checkCode


def sql_answer(code, preparation=''):
    header = f'sql = {code!r}\npreparation = {preparation!r}\n'
    return header + Path(__file__).with_name('sql_answer.py').read_text(encoding='utf-8')


def sql_program(code, preparation=''):
    return sql_answer(code, preparation) + '''
for index, result in enumerate(results, 1):
    print('Result', index)
    print(' | '.join(result['columns']))
    for row in result['rows']:
        print(repr(row))
if not results:
    print('SQL executed successfully (no result sets).')
'''


def check_sql(server, code, testcode, preparation='', files=None, cputime=None):
    return checkCode(server, sql_answer(code, preparation),
                     testcode + '\nimport answer\n', files=files, cputime=cputime)
