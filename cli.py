import requests

BASE_URL = "http://localhost:5000"

MENU = """
=== Inventory Management CLI ===
1. View all items
2. View a single item
3. Add a new item manually
4. Update an item's price or quantity
5. Delete an item
6. Find a product on OpenFoodFacts (no save)
7. Import a product from OpenFoodFacts into inventory
0. Exit
"""


class APIConnectionError(Exception):
    """Raised when the CLI cannot reach the Flask API."""
    pass


def _request(method: str, path: str, **kwargs) -> requests.Response:
    
    url = f"{BASE_URL}{path}"
    try:
        return requests.request(method, url, timeout=8, **kwargs)
    except requests.RequestException as exc:
        raise APIConnectionError(
            f"Could not reach the API at {url}. Is the Flask server running? ({exc})"
        ) from exc


def view_all_items():
    response = _request("GET", "/inventory")
    return response.status_code == 200, response.json()


def view_item(product_id: int):
    response = _request("GET", f"/inventory/{product_id}")
    return response.status_code == 200, response.json()


def add_item(product_name: str, barcode: str, price: float, quantity: int):
    payload = {
        "product_name": product_name,
        "barcode": barcode,
        "price": price,
        "quantity": quantity,
    }
    response = _request("POST", "/inventory", json=payload)
    return response.status_code == 201, response.json()


def update_item(product_id: int, **fields):
    """Update price, quantity, or any other field. e.g. update_item(3, price=4.5)"""
    response = _request("PATCH", f"/inventory/{product_id}", json=fields)
    return response.status_code == 200, response.json()


def delete_item(product_id: int):
    response = _request("DELETE", f"/inventory/{product_id}")
    return response.status_code == 200, response.json()


def find_on_external_api(barcode: str = None, name: str = None):
    """Look up a product on OpenFoodFacts without adding it to inventory."""
    params = {}
    if barcode:
        params["barcode"] = barcode
    if name:
        params["name"] = name
    response = _request("GET", "/products/lookup", params=params)
    return response.status_code == 200, response.json()


def import_from_external_api(barcode: str = None, name: str = None, price: float = 0.0, quantity: int = 0):
    """Fetch a product from OpenFoodFacts and add it to the inventory."""
    payload = {"price": price, "quantity": quantity}
    if barcode:
        payload["barcode"] = barcode
    if name:
        payload["name"] = name
    response = _request("POST", "/inventory/import", json=payload)
    return response.status_code == 201, response.json()

def _prompt(label, cast=str, required=True, default=None):
    while True:
        raw = input(f"{label}: ").strip()
        if not raw:
            if not required:
                return default
            if default is not None:
                return default
            print("This field is required.")
            continue
        try:
            return cast(raw)
        except ValueError:
            print(f"Please enter a valid {cast.__name__}.")


def main():
    print("Welcome to the Inventory Management CLI.")
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()

        try:
            if choice == "1":
                ok, data = view_all_items()
                print(data if ok else f"Error: {data}")

            elif choice == "2":
                product_id = _prompt("Product ID", int)
                ok, data = view_item(product_id)
                print(data if ok else f"Error: {data}")

            elif choice == "3":
                name = _prompt("Product name")
                barcode = _prompt("Barcode")
                price = _prompt("Price", float)
                quantity = _prompt("Quantity", int)
                ok, data = add_item(name, barcode, price, quantity)
                print(data if ok else f"Error: {data}")

            elif choice == "4":
                product_id = _prompt("Product ID", int)
                price = _prompt("New price (leave blank to skip)", float, required=False, default=None)
                quantity = _prompt("New quantity (leave blank to skip)", int, required=False, default=None)
                fields = {}
                if price is not None:
                    fields["price"] = price
                if quantity is not None:
                    fields["quantity"] = quantity
                ok, data = update_item(product_id, **fields)
                print(data if ok else f"Error: {data}")

            elif choice == "5":
                product_id = _prompt("Product ID", int)
                ok, data = delete_item(product_id)
                print(data if ok else f"Error: {data}")

            elif choice == "6":
                mode = _prompt("Search by 'barcode' or 'name'")
                if mode == "barcode":
                    ok, data = find_on_external_api(barcode=_prompt("Barcode"))
                else:
                    ok, data = find_on_external_api(name=_prompt("Product name"))
                print(data if ok else f"Error: {data}")

            elif choice == "7":
                mode = _prompt("Import by 'barcode' or 'name'")
                price = _prompt("Price to store", float)
                quantity = _prompt("Quantity", int)
                if mode == "barcode":
                    ok, data = import_from_external_api(barcode=_prompt("Barcode"), price=price, quantity=quantity)
                else:
                    ok, data = import_from_external_api(name=_prompt("Product name"), price=price, quantity=quantity)
                print(data if ok else f"Error: {data}")

            elif choice == "0":
                print("Goodbye!")
                break

            else:
                print("Invalid option, please try again.")

        except APIConnectionError as exc:
            print(f"Connection error: {exc}")


if __name__ == "__main__":
    main()
