CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category_id INTEGER REFERENCES categories(id));
INSERT INTO categories VALUES (1, 'Stationery'), (2, 'Books'), (3, 'Unused');
INSERT INTO products VALUES (1, 'Pen', 1), (2, 'Notebook', 1), (3, 'SQL Guide', 2);
