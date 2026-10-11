import sqlite3


def affordable_products(connection: sqlite3.Connection, max_price: float) -> list[str]:
    """Return product names with price strictly below max_price, ordered by name. Use the supplied connection and products(name TEXT, price REAL) table."""
    raise NotImplementedError
