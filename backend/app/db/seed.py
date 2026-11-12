"""Deterministic e-commerce seed data. Run: `python -m app.db.seed [--force]`."""

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from app.config import get_settings
from app.db.connection import connect_readwrite

SEED = 42
N_CUSTOMERS = 500
N_PRODUCTS = 120
N_ORDERS = 2000
SCHEMA_FILE = Path(__file__).with_name("schema.sql")
END_DATE = date(2025, 12, 31)

CATEGORIES = ["Electronics", "Books", "Clothing", "Home & Kitchen", "Sports", "Toys", "Beauty"]
FIRST_NAMES = [
    "Ava", "Liam", "Noah", "Emma", "Olivia", "Mia", "Lucas", "Ethan", "Sofia", "Aria",
    "Mateo", "Zoe", "Leo", "Nora", "Ravi", "Priya", "Yuki", "Chen", "Fatima", "Omar",
]  # fmt: skip
LAST_NAMES = [
    "Smith", "Garcia", "Kim", "Patel", "Nguyen", "Brown", "Silva", "Khan", "Rossi",
    "Muller", "Tanaka", "Ivanov", "Lopez", "Singh", "Wang", "Cohen", "Dubois", "Haddad",
]  # fmt: skip
LOCATIONS = [
    ("USA", "New York"), ("USA", "Austin"), ("Canada", "Toronto"), ("UK", "London"),
    ("Germany", "Berlin"), ("France", "Paris"), ("India", "Mumbai"), ("Japan", "Tokyo"),
    ("Brazil", "Sao Paulo"), ("Australia", "Sydney"),
]  # fmt: skip
PRODUCT_NOUNS = {
    "Electronics": ["Headphones", "Webcam", "Keyboard", "Monitor", "Charger", "Speaker"],
    "Books": ["Novel", "Cookbook", "Biography", "Atlas", "Textbook", "Journal"],
    "Clothing": ["T-Shirt", "Jacket", "Jeans", "Sneakers", "Scarf", "Hoodie"],
    "Home & Kitchen": ["Blender", "Lamp", "Cutting Board", "Kettle", "Pillow", "Pan"],
    "Sports": ["Yoga Mat", "Dumbbell", "Football", "Water Bottle", "Tent", "Racket"],
    "Toys": ["Puzzle", "Lego Set", "Doll", "Board Game", "RC Car", "Plush"],
    "Beauty": ["Moisturizer", "Shampoo", "Perfume", "Lipstick", "Sunscreen", "Serum"],
}
ADJECTIVES = ["Classic", "Pro", "Eco", "Ultra", "Compact", "Deluxe", "Basic", "Smart"]
STATUS_WEIGHTS = {"delivered": 70, "shipped": 12, "pending": 8, "cancelled": 10}


def _seed_categories(cur: sqlite3.Cursor) -> None:
    cur.executemany("INSERT INTO categories(id, name) VALUES (?, ?)", enumerate(CATEGORIES, 1))


def _seed_customers(cur: sqlite3.Cursor, rng: random.Random) -> None:
    rows = []
    for cid in range(1, N_CUSTOMERS + 1):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        country, city = rng.choice(LOCATIONS)
        joined = END_DATE - timedelta(days=rng.randint(30, 900))
        email = f"{first}.{last}{cid}@example.com".lower()
        rows.append((cid, first, last, email, country, city, joined.isoformat()))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?,?,?)", rows)


def _seed_products(cur: sqlite3.Cursor, rng: random.Random) -> None:
    rows = []
    for pid in range(1, N_PRODUCTS + 1):
        cat_id = rng.randint(1, len(CATEGORIES))
        noun = rng.choice(PRODUCT_NOUNS[CATEGORIES[cat_id - 1]])
        name = f"{rng.choice(ADJECTIVES)} {noun} {pid}"
        rows.append((pid, name, cat_id, round(rng.uniform(5, 600), 2), rng.randint(0, 500)))
    cur.executemany("INSERT INTO products VALUES (?,?,?,?,?)", rows)


def _seed_orders(cur: sqlite3.Cursor, rng: random.Random) -> None:
    prices = dict(cur.execute("SELECT id, price FROM products").fetchall())
    statuses, weights = zip(*STATUS_WEIGHTS.items(), strict=True)
    orders: list[tuple[int, int, str, str]] = []
    items: list[tuple[int, int, int, int, float]] = []
    for oid in range(1, N_ORDERS + 1):
        order_date = END_DATE - timedelta(days=rng.randint(0, 730))
        status = rng.choices(statuses, weights)[0]
        orders.append((oid, rng.randint(1, N_CUSTOMERS), order_date.isoformat(), status))
        for pid in rng.sample(range(1, N_PRODUCTS + 1), rng.randint(1, 4)):
            items.append((len(items) + 1, oid, pid, rng.randint(1, 5), prices[pid]))
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?)", orders)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?,?)", items)


def seed_database(db_path: Path, *, force: bool = False) -> None:
    if db_path.exists():
        if not force:
            raise FileExistsError(f"{db_path} exists. Use --force to rebuild.")
        db_path.unlink()
    rng = random.Random(SEED)  # noqa: S311 - deterministic fake data, not crypto
    conn = connect_readwrite(db_path)
    try:
        conn.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))
        cur = conn.cursor()
        _seed_categories(cur)
        _seed_customers(cur, rng)
        _seed_products(cur, rng)
        _seed_orders(cur, rng)
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the sample e-commerce database.")
    parser.add_argument("--force", action="store_true", help="Rebuild if the DB exists.")
    args = parser.parse_args()
    path = get_settings().database_path
    seed_database(path, force=args.force)
    print(f"Seeded {path}")  # noqa: T201


if __name__ == "__main__":
    main()
