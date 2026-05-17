import tempfile
import unittest
from pathlib import Path

from app import InventoryDatabase, Product


class InventoryDatabaseTest(unittest.TestCase):
    def test_add_stock_and_value(self):
        with tempfile.TemporaryDirectory() as folder:
            db = InventoryDatabase(Path(folder) / "test.db")
            db.add_product(Product("SKU1", "Keyboard", "Accessories", 50.0, 10, 3))
            db.update_stock("SKU1", 2, "OUT", "Sold items")

            product = db.get_product("SKU1")

            self.assertEqual(product.quantity, 8)
            self.assertEqual(db.inventory_value(), 400.0)
            db.close()

    def test_low_stock(self):
        with tempfile.TemporaryDirectory() as folder:
            db = InventoryDatabase(Path(folder) / "test.db")
            db.add_product(Product("SKU2", "Mouse", "Accessories", 20.0, 2, 5))

            rows = list(db.low_stock())

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["sku"], "SKU2")
            db.close()


if __name__ == "__main__":
    unittest.main()
