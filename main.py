from flask import Flask, jsonify, request
from api import get_product_by_barcode, get_product_by_name, ExternalAPIError

app = Flask(__name__)

inventory = []
_next_product_id = 1

def _reset_state():
    
    global inventory, _next_product_id
    inventory = []
    _next_product_id = 1


def _get_next_product_id() -> int:
    global _next_product_id
    current = _next_product_id
    _next_product_id += 1
    return current


def _find_item(product_id: int):
    return next((item for item in inventory if item["product_id"] == product_id), None)


def _validate_item_payload(data: dict, require_all: bool = True) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Request body must be a JSON object"

    required_fields = {"product_name", "barcode", "price", "quantity"}

    if require_all:
        missing = required_fields - data.keys()
        if missing:
            return False, f"Missing required field(s): {', '.join(sorted(missing))}"

    if "price" in data and not isinstance(data["price"], (int, float)):
        return False, "'price' must be a number"

    if "quantity" in data and not isinstance(data["quantity"], int):
        return False, "'quantity' must be an integer"

    if "barcode" in data and not isinstance(data["barcode"], str):
        return False, "'barcode' must be a string"

    return True, ""


@app.route("/inventory", methods=["GET"])
def get_inventory():
    """Fetch all inventory items."""
    return jsonify(inventory), 200


@app.route("/inventory/<int:product_id>", methods=["GET"])
def get_inventory_item(product_id):
    """Fetch a single inventory item by product_id."""
    item = _find_item(product_id)
    if item is None:
        return jsonify({"error": f"Product with product_id {product_id} not found"}), 404
    return jsonify(item), 200


@app.route("/inventory", methods=["POST"])
def create_inventory_item():
    """Add a new inventory item manually."""
    data = request.get_json(silent=True)
    valid, message = _validate_item_payload(data, require_all=True)
    if not valid:
        return jsonify({"error": message}), 400

    item = {
        "product_id": _get_next_product_id(),
        "product_name": data["product_name"],
        "barcode": data["barcode"],
        "quantity": data["quantity"],
        "price": data["price"],
    }
    inventory.append(item)
    return jsonify(item), 201


@app.route("/inventory/<int:product_id>", methods=["PATCH"])
def update_inventory_item(product_id):
    
    item = _find_item(product_id)
    if item is None:
        return jsonify({"error": f"Product with product_id {product_id} not found"}), 404

    data = request.get_json(silent=True)
    valid, message = _validate_item_payload(data, require_all=False)
    if not valid:
        return jsonify({"error": message}), 400

    updatable_fields = {"product_name", "barcode", "quantity", "price"}
    for field in updatable_fields:
        if field in data:
            item[field] = data[field]

    return jsonify(item), 200


@app.route("/inventory/<int:product_id>", methods=["DELETE"])
def delete_inventory_item(product_id):
    
    item = _find_item(product_id)
    if item is None:
        return jsonify({"error": f"Product with product_id {product_id} not found"}), 404

    inventory.remove(item)
    return jsonify({"message": f"Product with product_id {product_id} deleted"}), 200

@app.route("/products/lookup", methods=["GET"])
def lookup_product():
    """
    Look up a product from OpenFoodFacts WITHOUT adding it to inventory.
    Query params: ?barcode=<code>  OR  ?name=<product name>
    """
    barcode = request.args.get("barcode")
    name = request.args.get("name")

    if not barcode and not name:
        return jsonify({"error": "Provide a 'barcode' or 'name' query parameter"}), 400

    try:
        if barcode:
            product = get_product_by_barcode(barcode)
        else:
            product = get_product_by_name(name)
    except ExternalAPIError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify(product), 200


@app.route("/inventory/import", methods=["POST"])
def import_inventory_item():
    """
    Fetch a product from OpenFoodFacts and add it to the inventory array.
    Body JSON: {"barcode": "..."} or {"name": "..."}
    Optional overrides: "price", "quantity"
    """
    data = request.get_json(silent=True) or {}
    barcode = data.get("barcode")
    name = data.get("name")

    if not barcode and not name:
        return jsonify({"error": "Provide 'barcode' or 'name' in the request body"}), 400

    try:
        if barcode:
            product = get_product_by_barcode(barcode)
        else:
            product = get_product_by_name(name)
    except ExternalAPIError as exc:
        return jsonify({"error": str(exc)}), 502

    item = {
        "product_id": _get_next_product_id(),
        "product_name": product["product_name"],
        "barcode": product.get("barcode") or barcode or "",
        "quantity": data.get("quantity", 0),
        "price": data.get("price", 0.0),
    }
    inventory.append(item)
    return jsonify(item), 201


if __name__ == "__main__":
    app.run(debug=True)
