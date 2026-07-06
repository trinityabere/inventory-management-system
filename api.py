import requests

BASE_URL = "https://world.openfoodfacts.org"
REQUEST_TIMEOUT = 8  # seconds
# See: https://openfoodfacts.github.io/openfoodfacts-server/api/
HEADERS = {
    "User-Agent": "InventoryManagementLab/1.0 (student@example.com)"
}

class ExternalAPIError(Exception):
    pass


def get_product_by_barcode(barcode: str) -> dict:
    
    # v3 is the current, recommended API version for product reads.
    url = f"{BASE_URL}/api/v3/product/{barcode}.json"

    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExternalAPIError(f"Failed to reach OpenFoodFacts API: {exc}") from exc

    data = response.json()

    if data.get("status") != 1:
        raise ExternalAPIError(f"No product found for barcode '{barcode}'")

    product = data.get("product", {})
    return _normalize_product(product, barcode=barcode)


def get_product_by_name(name: str) -> dict:
    
    url = f"{BASE_URL}/cgi/search.pl"
    params = {
        "search_terms": name,
        "json": 1,
        "page_size": 1,
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ExternalAPIError(f"Failed to reach OpenFoodFacts API: {exc}") from exc

    data = response.json()
    products = data.get("products", [])

    if not products:
        raise ExternalAPIError(f"No product found for name '{name}'")

    product = products[0]
    return _normalize_product(product, barcode=product.get("code"))


def _normalize_product(product: dict, barcode: str = None) -> dict:
    """Extract just the fields we care about, with safe fallbacks."""
    return {
        "barcode": product.get("code", barcode),
        "product_name": product.get("product_name") or "Unknown product",
        "brands": product.get("brands", ""),
        "ingredients_text": product.get("ingredients_text", ""),
        "categories": product.get("categories", ""),
        "image_url": product.get("image_url"),
    }
