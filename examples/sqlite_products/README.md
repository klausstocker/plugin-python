# SQLite

Return product names with price strictly below max_price, ordered by name. Use the supplied connection and products(name TEXT, price REAL) table.

Each test gets a fresh in-memory SQLite database. The reference solution binds the price as a SQL parameter and explicitly sorts results. No database file or server is needed.

- `template.py`: typed student starter used as the indication.
- `answer.py`: working reference solution.
- `test_answer.py`: teacher validation.

From this directory, run `python -m unittest test_answer.py`.

See [the examples guide](../README.md) for setup and all examples.
