import sqlite3


def affordable_products(connection: sqlite3.Connection, max_price: float) -> list[str]:
    rows = connection.execute(
        "SELECT name FROM products WHERE price < ? ORDER BY name", (max_price,)
    )
    return [row[0] for row in rows]
