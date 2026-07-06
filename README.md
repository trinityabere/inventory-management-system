# Inventory Management System

A Flask REST API for managing retail inventory, with real-time product
enrichment from the [OpenFoodFacts API](https://world.openfoodfacts.org/data),
a CLI client, and a full pytest test suite.

## Features

- Full CRUD REST API for inventory items (`GET`, `POST`, `PATCH`, `DELETE`)
- External API integration: look up products by barcode or name via OpenFoodFacts
- One-step "import" endpoint that fetches a product and adds it straight to inventory
- CLI tool that talks to the API over HTTP
- Unit tests for the API, the external API integration, and the CLI (all network calls mocked)

## Project Structure

```
inventory-management/
├── main.py                 # Flask REST API
├── api.py         # OpenFoodFacts integration
├── cli.py                  # Command-line client
├── requirements.txt
├── README.md
└── tests/
    ├── test_main.py          # API route tests
    ├── test_api.py # External API tests (mocked)
    └── test_cli.py          # CLI tests (mocked)
```

## Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd inventory-management
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv myenv
   source myenv/bin/activate # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask API**
   ```bash
   flask --app main run --debug
   ```
   The API will be available at `http://localhost:5000`.

5. **Run the CLI (in a separate terminal, with the server running)**
   ```bash
   python cli.py
   ```

6. **Run the tests**
   ```bash
   pytest -v
   ```

## Notes on the OpenFoodFacts API

- Every request sends a custom `User-Agent` header, as OpenFoodFacts asks
  all integrations to identify themselves (`AppName/Version (contact)`).
  This is set in `api.py` and should be updated with your own
  contact email if you deploy this for real use.
- Product lookups by barcode use the current **v3** API
  (`/api/v3/product/<barcode>.json`). Name search uses the legacy
  `/cgi/search.pl` endpoint, since full-text search isn't available on
  the v2/v3 structured-search APIs.
- OpenFoodFacts rate-limits requests: **15/min** for product reads,
  **10/min** for searches. This lab's usage is well within those limits,
  but it's worth knowing if you scale this up.
- For development/testing without touching production data, OpenFoodFacts
  offers a staging environment at `https://world.openfoodfacts.net`
  (HTTP basic auth: `off` / `off`). Swapping `BASE_URL` in
  `api.py` is enough to point at staging.

## Data Model

Every inventory item has exactly these attributes — no extras:

| Attribute      | Type    | Required | Notes                                      |
|----------------|---------|----------|---------------------------------------------|
| `product_id`   | integer | system-generated | Unique identifier, assigned automatically |
| `product_name` | string  | yes      | Name of the product                         |
| `barcode`      | string  | yes      | Used to match against OpenFoodFacts         |
| `quantity`     | integer | yes      | Units in stock                              |
| `price`        | number  | yes      | Unit price                                  |

When you import a product from OpenFoodFacts, only `product_name` and
`barcode` are pulled from the external data — everything else OpenFoodFacts
returns (brand, ingredients, categories, images, etc.) is discarded before
the item is saved to inventory, keeping every stored item to this same
five-attribute shape.

## API Endpoints

### Inventory CRUD

| Method | Endpoint                    | Description                     |
|--------|------------------------------|----------------------------------|
| GET    | `/inventory`                | Fetch all inventory items       |
| GET    | `/inventory/<product_id>`   | Fetch a single item by product_id |
| POST   | `/inventory`                | Add a new item manually          |
| PATCH  | `/inventory/<product_id>`   | Update an existing item          |
| DELETE | `/inventory/<product_id>`   | Remove an item                   |

**POST /inventory** body example:
```json
{
  "product_name": "Organic Almond Milk",
  "barcode": "0018627",
  "price": 4.99,
  "quantity": 20
}
```
All four fields (`product_name`, `barcode`, `price`, `quantity`) are required.

**PATCH /inventory/<product_id>** body example (any subset of fields):
```json
{ "price": 5.49, "quantity": 15 }
```

### External API (OpenFoodFacts)

| Method | Endpoint                          | Description                                              |
|--------|------------------------------------|------------------------------------------------------------|
| GET    | `/products/lookup?barcode=<code>` | Look up a product by barcode (not saved to inventory)      |
| GET    | `/products/lookup?name=<name>`    | Look up a product by name (not saved to inventory)         |
| POST   | `/inventory/import`               | Fetch a product from OpenFoodFacts and add it to inventory |

**POST /inventory/import** body example:
```json
{ "barcode": "0018627", "price": 4.99, "quantity": 20 }
```
or
```json
{ "name": "peanut butter", "price": 3.50, "quantity": 12 }
```

All error responses return `{"error": "<message>"}` with an appropriate
HTTP status code (`400` bad request, `404` not found, `502` external API failure).

## CLI Usage

After starting the Flask server, run:
```bash
python cli.py
```

You'll see a menu:
```
=== Inventory Management CLI ===
1. View all items
2. View a single item
3. Add a new item manually
4. Update an item's price or quantity
5. Delete an item
6. Find a product on OpenFoodFacts (no save)
7. Import a product from OpenFoodFacts into inventory
0. Exit
```

Example: importing a product by barcode.
```
Choose an option: 7
Import by 'barcode' or 'name': barcode
Price to store: 4.99
Quantity: 20
Barcode: 0018627
{'product_id': 1, 'product_name': 'Organic Almond Milk', 'barcode': '0018627', 'quantity': 20, 'price': 4.99}
```

## Testing

The test suite covers:
- Every CRUD route, including error cases (missing fields, not-found IDs, bad types)
- External API integration (success, not-found, and network-failure cases), fully mocked with `unittest.mock`
- Every CLI action function, with the underlying `requests` calls mocked

Run everything with:
```bash
pytest -v
```

## Git Workflow

This project follows a feature-branch workflow:
- `main` — stable, always-working code
- `external-apis` — OpenFoodFacts integration
- `cli` — CLI client
- `tests` — test suite
- `docs` _ README and requirements

Each feature was developed on its own branch and merged into `main` via
pull request once tests passed.
