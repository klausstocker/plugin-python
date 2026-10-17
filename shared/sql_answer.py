"""Runtime shipped to Jobe as answer.py; student input is always SQL data."""
import sqlite3


def execute_statements(connection, source):
    """Keep every result set, including RETURNING; respect strings and triggers."""
    results = []
    start = 0
    for index, char in enumerate(source):
        if char == ';' and sqlite3.complete_statement(source[start:index + 1]):
            _execute(connection, source[start:index + 1], results)
            start = index + 1
    if source[start:].strip():
        _execute(connection, source[start:], results)
    return results


def _execute(connection, statement, results):
    cursor = connection.execute(statement)
    if cursor.description is not None:
        results.append({'columns': [column[0] for column in cursor.description],
                        'rows': cursor.fetchall()})


def reset():
    """Recreate the fixture and rerun the submission (also usable in setUp)."""
    global connection, results, rows, columns
    if 'connection' in globals():
        connection.close()
    connection = sqlite3.connect(':memory:')
    connection.execute('PRAGMA foreign_keys = ON')
    connection.executescript(preparation)
    connection.commit()

    # Student SQL stays inside this database, even when ATTACH uses a URI.
    connection.set_authorizer(lambda action, *args: sqlite3.SQLITE_DENY
                              if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH)
                              else sqlite3.SQLITE_OK)
    results = execute_statements(connection, sql)
    rows = results[-1]['rows'] if results else []
    columns = results[-1]['columns'] if results else []


reset()
