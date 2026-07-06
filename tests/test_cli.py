from unittest.mock import patch, MagicMock

import cli


def _mock_response(json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    return mock_resp


@patch("cli.requests.request")
def test_view_all_items_success(mock_request):
    mock_request.return_value = _mock_response([{"product_id": 1, "product_name": "Milk"}])

    ok, data = cli.view_all_items()

    assert ok is True
    assert data[0]["product_name"] == "Milk"
    mock_request.assert_called_once_with("GET", "http://localhost:5000/inventory", timeout=8)


@patch("cli.requests.request")
def test_view_item_not_found(mock_request):
    mock_request.return_value = _mock_response({"error": "not found"}, status_code=404)

    ok, data = cli.view_item(999)

    assert ok is False
    assert "error" in data


@patch("cli.requests.request")
def test_add_item_success(mock_request):
    mock_request.return_value = _mock_response(
        {"product_id": 1, "product_name": "Bread", "barcode": "555", "price": 3.5, "quantity": 10},
        status_code=201,
    )

    ok, data = cli.add_item("Bread", "555", 3.5, 10)

    assert ok is True
    assert data["product_name"] == "Bread"
    args, kwargs = mock_request.call_args
    assert kwargs["json"]["product_name"] == "Bread"
    assert kwargs["json"]["barcode"] == "555"
    assert kwargs["json"]["quantity"] == 10


@patch("cli.requests.request")
def test_update_item_success(mock_request):
    mock_request.return_value = _mock_response({"product_id": 1, "price": 9.99})

    ok, data = cli.update_item(1, price=9.99)

    assert ok is True
    assert data["price"] == 9.99


@patch("cli.requests.request")
def test_delete_item_success(mock_request):
    mock_request.return_value = _mock_response({"message": "deleted"})

    ok, data = cli.delete_item(1)

    assert ok is True
    assert "message" in data


@patch("cli.requests.request")
def test_find_on_external_api(mock_request):
    mock_request.return_value = _mock_response({"product_name": "Test Product"})

    ok, data = cli.find_on_external_api(barcode="12345")

    assert ok is True
    assert data["product_name"] == "Test Product"


@patch("cli.requests.request")
def test_import_from_external_api(mock_request):
    mock_request.return_value = _mock_response(
        {"product_id": 2, "product_name": "Imported Item", "barcode": "999", "quantity": 8, "price": 4.0},
        status_code=201,
    )

    ok, data = cli.import_from_external_api(name="cereal", price=4.0, quantity=8)

    assert ok is True
    assert data["product_name"] == "Imported Item"
    assert data["quantity"] == 8


@patch("cli.requests.request")
def test_connection_error_raises_custom_exception(mock_request):
    import requests as real_requests
    mock_request.side_effect = real_requests.ConnectionError("refused")

    try:
        cli.view_all_items()
        assert False, "Expected APIConnectionError to be raised"
    except cli.APIConnectionError as exc:
        assert "Is the Flask server running" in str(exc)
