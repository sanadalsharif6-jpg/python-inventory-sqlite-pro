# Python Inventory SQLite Pro

A professional command-line inventory system built with Python and SQLite.

## Features

- SQLite database storage
- Product management
- Stock IN / OUT movements
- Low-stock report
- Category report
- Total inventory value calculation
- CSV export
- Unit tests

## Run Examples

Add a product:

```bash
python app.py add --sku P001 --name "Mechanical Keyboard" --category Accessories --price 80 --quantity 12 --reorder 4
```

List products:

```bash
python app.py list
```

Sell stock:

```bash
python app.py stock --sku P001 --type OUT --quantity 2 --note "Customer order"
```

Restock:

```bash
python app.py stock --sku P001 --type IN --quantity 10 --note "Supplier delivery"
```

Low-stock report:

```bash
python app.py low-stock
```

Category report:

```bash
python app.py category-report
```

Export CSV:

```bash
python app.py export --path inventory_report.csv
```

## Test

```bash
python -m unittest
```
