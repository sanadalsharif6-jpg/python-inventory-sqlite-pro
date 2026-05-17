import argparse
import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DB_PATH = Path("inventory.db")


@dataclass
class Product:
    sku: str
    name: str
    category: str
    price: float
    quantity: int
    reorder_level: int


class InventoryDatabase:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                sku TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL CHECK(price >= 0),
                quantity INTEGER NOT NULL CHECK(quantity >= 0),
                reorder_level INTEGER NOT NULL CHECK(reorder_level >= 0)
            )
            """
        )
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                movement_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                note TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sku) REFERENCES products(sku)
            )
            """
        )
        self.connection.commit()

    def add_product(self, product: Product):
        self.connection.execute(
            """
            INSERT INTO products (sku, name, category, price, quantity, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                product.sku,
                product.name,
                product.category,
                product.price,
                product.quantity,
                product.reorder_level,
            ),
        )
        self.connection.execute(
            """
            INSERT INTO stock_movements (sku, movement_type, quantity, note)
            VALUES (?, 'INITIAL', ?, 'Initial stock')
            """,
            (product.sku, product.quantity),
        )
        self.connection.commit()

    def update_stock(self, sku: str, quantity: int, movement_type: str, note: str = ""):
        product = self.get_product(sku)
        if product is None:
            raise ValueError("Product not found.")

        movement_type = movement_type.upper()
        if movement_type not in {"IN", "OUT"}:
            raise ValueError("Movement type must be IN or OUT.")
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        new_quantity = product.quantity + quantity if movement_type == "IN" else product.quantity - quantity
        if new_quantity < 0:
            raise ValueError("Not enough stock.")

        self.connection.execute(
            "UPDATE products SET quantity = ? WHERE sku = ?",
            (new_quantity, sku),
        )
        self.connection.execute(
            """
            INSERT INTO stock_movements (sku, movement_type, quantity, note)
            VALUES (?, ?, ?, ?)
            """,
            (sku, movement_type, quantity, note),
        )
        self.connection.commit()

    def get_product(self, sku: str):
        row = self.connection.execute(
            "SELECT * FROM products WHERE sku = ?",
            (sku,),
        ).fetchone()
        return Product(**dict(row)) if row else None

    def list_products(self) -> Iterable[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT sku, name, category, price, quantity, reorder_level,
                   price * quantity AS total_value
            FROM products
            ORDER BY category, name
            """
        ).fetchall()

    def low_stock(self) -> Iterable[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT sku, name, category, quantity, reorder_level
            FROM products
            WHERE quantity <= reorder_level
            ORDER BY quantity ASC
            """
        ).fetchall()

    def inventory_value(self) -> float:
        row = self.connection.execute(
            "SELECT COALESCE(SUM(price * quantity), 0) AS value FROM products"
        ).fetchone()
        return float(row["value"])

    def category_report(self) -> Iterable[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT category,
                   COUNT(*) AS products,
                   SUM(quantity) AS units,
                   SUM(price * quantity) AS value
            FROM products
            GROUP BY category
            ORDER BY value DESC
            """
        ).fetchall()

    def movement_history(self, sku: str) -> Iterable[sqlite3.Row]:
        return self.connection.execute(
            """
            SELECT movement_type, quantity, note, created_at
            FROM stock_movements
            WHERE sku = ?
            ORDER BY created_at DESC, id DESC
            """,
            (sku,),
        ).fetchall()

    def export_csv(self, path: Path):
        rows = self.list_products()
        with Path(path).open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["sku", "name", "category", "price", "quantity", "reorder_level", "total_value"])
            for row in rows:
                writer.writerow([
                    row["sku"],
                    row["name"],
                    row["category"],
                    f"{row['price']:.2f}",
                    row["quantity"],
                    row["reorder_level"],
                    f"{row['total_value']:.2f}",
                ])

    def close(self):
        self.connection.close()


def print_table(rows):
    rows = list(rows)
    if not rows:
        print("No data found.")
        return

    headers = rows[0].keys()
    widths = {
        header: max(len(str(header)), max(len(str(row[header])) for row in rows))
        for header in headers
    }

    header_line = " | ".join(str(header).ljust(widths[header]) for header in headers)
    print(header_line)
    print("-" * len(header_line))

    for row in rows:
        print(" | ".join(str(row[header]).ljust(widths[header]) for header in headers))


def build_parser():
    parser = argparse.ArgumentParser(description="Professional SQLite Inventory Management System")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="Add a new product")
    add.add_argument("--sku", required=True)
    add.add_argument("--name", required=True)
    add.add_argument("--category", required=True)
    add.add_argument("--price", type=float, required=True)
    add.add_argument("--quantity", type=int, required=True)
    add.add_argument("--reorder", type=int, default=5)

    stock = sub.add_parser("stock", help="Update product stock")
    stock.add_argument("--sku", required=True)
    stock.add_argument("--type", choices=["IN", "OUT"], required=True)
    stock.add_argument("--quantity", type=int, required=True)
    stock.add_argument("--note", default="")

    sub.add_parser("list", help="List all products")
    sub.add_parser("low-stock", help="Show low stock products")
    sub.add_parser("value", help="Show total inventory value")
    sub.add_parser("category-report", help="Show category report")

    history = sub.add_parser("history", help="Show movement history for one product")
    history.add_argument("--sku", required=True)

    export = sub.add_parser("export", help="Export inventory report to CSV")
    export.add_argument("--path", default="inventory_report.csv")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    db = InventoryDatabase()

    try:
        if args.command == "add":
            db.add_product(
                Product(
                    sku=args.sku,
                    name=args.name,
                    category=args.category,
                    price=args.price,
                    quantity=args.quantity,
                    reorder_level=args.reorder,
                )
            )
            print("Product added successfully.")

        elif args.command == "stock":
            db.update_stock(args.sku, args.quantity, args.type, args.note)
            print("Stock updated successfully.")

        elif args.command == "list":
            print_table(db.list_products())

        elif args.command == "low-stock":
            print_table(db.low_stock())

        elif args.command == "value":
            print(f"Total inventory value: ${db.inventory_value():.2f}")

        elif args.command == "category-report":
            print_table(db.category_report())

        elif args.command == "history":
            print_table(db.movement_history(args.sku))

        elif args.command == "export":
            db.export_csv(Path(args.path))
            print(f"Report exported to {args.path}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
