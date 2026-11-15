"""Golden questions with hand-written reference SQL. Results (not SQL text) are compared."""

from typing import NamedTuple


class GoldenCase(NamedTuple):
    question: str
    reference_sql: str


_REVENUE = "SUM(oi.quantity * oi.unit_price)"

GOLDEN_CASES: tuple[GoldenCase, ...] = (
    GoldenCase("How many customers are there?", "SELECT COUNT(*) FROM customers"),
    GoldenCase("How many products do we sell?", "SELECT COUNT(*) FROM products"),
    GoldenCase("List all product categories", "SELECT name FROM categories ORDER BY name"),
    GoldenCase(
        "How many customers are from each country? Most first.",
        "SELECT country, COUNT(*) AS n FROM customers GROUP BY country ORDER BY n DESC, country",
    ),
    GoldenCase(
        "How many orders have each status?",
        "SELECT status, COUNT(*) AS n FROM orders GROUP BY status",
    ),
    GoldenCase(
        "How many orders were cancelled?",
        "SELECT COUNT(*) FROM orders WHERE status = 'cancelled'",
    ),
    GoldenCase(
        "What is the average product price?",
        "SELECT ROUND(AVG(price), 2) FROM products",
    ),
    GoldenCase(
        "What is the most expensive product? Show its name and price.",
        "SELECT name, price FROM products ORDER BY price DESC LIMIT 1",
    ),
    GoldenCase(
        "Show the 5 cheapest products with their prices.",
        "SELECT name, price FROM products ORDER BY price ASC, name LIMIT 5",
    ),
    GoldenCase(
        "Which products are out of stock?",
        "SELECT name FROM products WHERE stock = 0",
    ),
    GoldenCase(
        "How many orders were placed in 2024?",
        "SELECT COUNT(*) FROM orders WHERE order_date LIKE '2024%'",
    ),
    GoldenCase(
        "How many orders were placed in each year?",
        "SELECT strftime('%Y', order_date) AS year, COUNT(*) FROM orders GROUP BY year",
    ),
    GoldenCase(
        "What is the total revenue?",
        f"SELECT ROUND({_REVENUE}, 2) FROM order_items oi "
        "JOIN orders o ON o.id = oi.order_id WHERE o.status != 'cancelled'",
    ),
    GoldenCase(
        "What is the total revenue from delivered orders?",
        f"SELECT ROUND({_REVENUE}, 2) FROM order_items oi "
        "JOIN orders o ON o.id = oi.order_id WHERE o.status = 'delivered'",
    ),
    GoldenCase(
        "Top 5 customers by total spend, with their first and last name.",
        f"SELECT c.first_name, c.last_name, ROUND({_REVENUE}, 2) AS spend FROM customers c "
        "JOIN orders o ON o.customer_id = c.id JOIN order_items oi ON oi.order_id = o.id "
        "WHERE o.status != 'cancelled' GROUP BY c.id ORDER BY spend DESC LIMIT 5",
    ),
    GoldenCase(
        "Revenue per product category, highest first.",
        f"SELECT cat.name, ROUND({_REVENUE}, 2) AS revenue FROM categories cat "
        "JOIN products p ON p.category_id = cat.id JOIN order_items oi ON oi.product_id = p.id "
        "JOIN orders o ON o.id = oi.order_id WHERE o.status != 'cancelled' "
        "GROUP BY cat.id ORDER BY revenue DESC",
    ),
    GoldenCase(
        "Which category has the most products? Show only its name.",
        "SELECT cat.name FROM categories cat JOIN products p ON p.category_id = cat.id "
        "GROUP BY cat.id ORDER BY COUNT(*) DESC, cat.name LIMIT 1",
    ),
    GoldenCase(
        "How many customers have never placed an order?",
        "SELECT COUNT(*) FROM customers c "
        "WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id)",
    ),
    GoldenCase(
        "What is the average number of items per order? Show only the average.",
        "SELECT ROUND(AVG(items), 2) FROM "
        "(SELECT SUM(quantity) AS items FROM order_items GROUP BY order_id)",
    ),
    GoldenCase(
        "Top 3 best-selling products by units sold.",
        "SELECT p.name, SUM(oi.quantity) AS units FROM products p "
        "JOIN order_items oi ON oi.product_id = p.id GROUP BY p.id ORDER BY units DESC, p.name "
        "LIMIT 3",
    ),
    GoldenCase(
        "How many orders did each customer from Japan place? Show first name and count.",
        "SELECT c.first_name, COUNT(o.id) AS orders FROM customers c "
        "LEFT JOIN orders o ON o.customer_id = c.id WHERE c.country = 'Japan' GROUP BY c.id",
    ),
    GoldenCase(
        "Which country generates the most revenue? Show only the country.",
        "SELECT c.country FROM customers c JOIN orders o ON o.customer_id = c.id "
        "JOIN order_items oi ON oi.order_id = o.id WHERE o.status != 'cancelled' "
        "GROUP BY c.country "
        f"ORDER BY {_REVENUE} DESC LIMIT 1",
    ),
    GoldenCase(
        "Monthly order counts for 2025.",
        "SELECT strftime('%Y-%m', order_date) AS month, COUNT(*) FROM orders "
        "WHERE order_date LIKE '2025%' GROUP BY month ORDER BY month",
    ),
    GoldenCase(
        "List the Electronics products priced above 400, with price.",
        "SELECT p.name, p.price FROM products p JOIN categories c ON c.id = p.category_id "
        "WHERE c.name = 'Electronics' AND p.price > 400",
    ),
    GoldenCase(
        "How many customers signed up in 2024?",
        "SELECT COUNT(*) FROM customers WHERE created_at LIKE '2024%'",
    ),
    GoldenCase(
        "What percentage of orders were cancelled? Round to 1 decimal.",
        "SELECT ROUND(100.0 * SUM(status = 'cancelled') / COUNT(*), 1) FROM orders",
    ),
)
