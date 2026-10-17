SELECT p.name AS product, c.name AS category
FROM products AS p
JOIN categories AS c ON p.category_id = c.id
ORDER BY p.name;
