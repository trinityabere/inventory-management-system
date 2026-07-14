import pytest
from unittest.mock import patch

import main as app_module
from main import app
from api import ExternalAPIError


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app_module._reset_state()
    with app.test_client() as test_client:
        yield test_client
    app_module._reset_state()


def _create_sample_item(client, **overrides):
    payload = {
        "product_name": "Organic Almond Milk",
        "barcode": "0018627",
        "price": 4.99,
        "quantity": 20,
    }
    payload.update(overrides)
    return client.post("/inventory", json=payload)



# GET /inventory


def test_get_inventory_empty(client):
    response = client.get("/inventory")
    assert response.status_code == 200
    assert response.get_json() == []


def test_get_inventory_returns_items(client):
    _create_sample_item(client)
    response = client.get("/inventory")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 1
    assert data[0]["product_name"] == "Organic Almond Milk"
    assert data[0]["barcode"] == "0018627"




def test_get_single_item(client):
    create_resp = _create_sample_item(client)
    product_id = create_resp.get_json()["product_id"]

    response = client.get(f"/inventory/{product_id}")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Organic Almond Milk"


def test_get_single_item_not_found(client):
    response = client.get("/inventory/999")
    assert response.status_code == 404
    assert "error" in response.get_json()



def test_create_item_success(client):
    response = _create_sample_item(client)
    assert response.status_code == 201
    data = response.get_json()
    assert data["product_id"] == 1
    assert data["quantity"] == 20
    assert set(data.keys()) == {"product_id", "product_name", "barcode", "quantity", "price"}


def test_create_item_missing_required_field(client):
    response = client.post("/inventory", json={"product_name": "Missing fields"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_create_item_missing_barcode(client):
    response = client.post("/inventory", json={
        "product_name": "No Barcode", "price": 1.0, "quantity": 1,
    })
    assert response.status_code == 400
    assert "barcode" in response.get_json()["error"]


def test_create_item_invalid_price_type(client):
    response = client.post("/inventory", json={
        "product_name": "Bad Price", "barcode": "111", "price": "free", "quantity": 5,
    })
    assert response.status_code == 400


def test_create_item_invalid_quantity_type(client):
    response = client.post("/inventory", json={
        "product_name": "Bad Quantity", "barcode": "111", "price": 1.0, "quantity": "lots",
    })
    assert response.status_code == 400

# PATCH /inventory/<product_id>


def test_update_item_success(client):
    create_resp = _create_sample_item(client)
    product_id = create_resp.get_json()["product_id"]

    response = client.patch(f"/inventory/{product_id}", json={"price": 5.49, "quantity": 15})
    assert response.status_code == 200
    data = response.get_json()
    assert data["price"] == 5.49
    assert data["quantity"] == 15


def test_update_item_not_found(client):
    response = client.patch("/inventory/999", json={"price": 1.0})
    assert response.status_code == 404


# DELETE /inventory/<product_id>


def test_delete_item_success(client):
    create_resp = _create_sample_item(client)
    product_id = create_resp.get_json()["product_id"]

    response = client.delete(f"/inventory/{product_id}")
    assert response.status_code == 200

    follow_up = client.get(f"/inventory/{product_id}")
    assert follow_up.status_code == 404


def test_delete_item_not_found(client):
    response = client.delete("/inventory/999")
    assert response.status_code == 404




@patch("main.get_product_by_barcode")
def test_lookup_product_by_barcode(mock_get, client):
    mock_get.return_value = {
        "barcode": "12345",
        "product_name": "Test Cereal",
        "brands": "TestBrand",
        "ingredients_text": "oats, sugar",
        "categories": "cereals",
        "image_url": None,
    }
    response = client.get("/products/lookup?barcode=12345")
    assert response.status_code == 200
    assert response.get_json()["product_name"] == "Test Cereal"
    mock_get.assert_called_once_with("12345")


@patch("main.get_product_by_name")
def test_lookup_product_by_name(mock_get, client):
    mock_get.return_value = {"barcode": "", "product_name": "Test Soda", "brands": "", "ingredients_text": "", "categories": "", "image_url": None}
    response = client.get("/products/lookup?name=Test+Soda")
    assert response.status_code == 200
    mock_get.assert_called_once_with("Test Soda")


def test_lookup_product_missing_params(client):
    response = client.get("/products/lookup")
    assert response.status_code == 400


@patch("main.get_product_by_barcode")
def test_lookup_product_external_api_failure(mock_get, client):
    mock_get.side_effect = ExternalAPIError("No product found for barcode '000'")
    response = client.get("/products/lookup?barcode=000")
    assert response.status_code == 502
    assert "error" in response.get_json()



@patch("main.get_product_by_barcode")
def test_import_item_success(mock_get, client):
    mock_get.return_value = {
        "barcode": "12345",
        "product_name": "Imported Snack",
        "brands": "SnackCo",
        "ingredients_text": "corn, salt",
        "categories": "snacks",
        "image_url": None,
    }
    response = client.post("/inventory/import", json={"barcode": "12345", "price": 2.5, "quantity": 10})
    assert response.status_code == 201
    data = response.get_json()
    assert data["product_name"] == "Imported Snack"
    assert data["price"] == 2.5
    assert data["quantity"] == 10
    assert data["barcode"] == "12345"
    assert set(data.keys()) == {"product_id", "product_name", "barcode", "quantity", "price"}

    # Confirm it was actually added to the inventory array
    inventory_resp = client.get("/inventory")
    assert len(inventory_resp.get_json()) == 1


def test_import_item_missing_identifier(client):
    response = client.post("/inventory/import", json={"price": 1.0, "quantity": 1})
    assert response.status_code == 400


@patch("main.get_product_by_name")
def test_import_item_external_api_failure(mock_get, client):
    mock_get.side_effect = ExternalAPIError("No product found for name 'nonexistent'")
    response = client.post("/inventory/import", json={"name": "nonexistent"})
    assert response.status_code == 502
