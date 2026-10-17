# SQL exercises

Select an example in the configuration dialog's UnitTest tab and click Apply.
Applying loads preparation SQL, starter SQL, Python tests, and default options;
replacing existing code requires confirmation.

| Example | Task |
| --- | --- |
| 01 select_products | The original SELECT example: return products ordered by price. |
| 02 insert_products | Insert Ruler and return all products. |
| 03 update_prices | Increase prices and return the updated products. |
| 04 delete_products | Delete products with no stock and return the remaining products. |
| 05 join_products | Join products to their categories. |

Each folder includes `preparation.sql`, `template.sql`, `test_answer.py`, and
`solution.sql`. The SELECT example works immediately. The other starters need
completing; every reference solution earns full credit. Tests check returned
rows and database contents so returning literal rows cannot substitute for
required INSERT, UPDATE, or DELETE changes.

Each Jobe execution creates a new in-memory database from the preparation SQL. See
[SQL help](../../resources/help/SQL.html) for the test API.
