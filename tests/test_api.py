import pytest
from unittest.mock import patch, MagicMock
import requests

from api import get_product_by_barcode, get_product_by_name, ExternalAPIError


def _mock_response(json_data, status_code=200, raise_for_status_error=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    if raise_for_status_error:
        mock_resp.raise_for_status.side_effect = raise_for_status_error
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


@patch("api.requests.get")
def test_get_product_by_barcode_success(mock_get):
    mock_get.return_value = _mock_response({
        "status": 1,
        "product": {
            "code": "0018627",
            "product_name": "Organic Almond Milk",
            "brands": "Silk",
            "ingredients_text": "Filtered water, almonds, cane sugar",
            "categories": "Dairy alternatives",
            "image_url": "http://example.com/img.jpg",
        }
    })

    result = get_product_by_barcode("0018627")

    assert result["product_name"] == "Organic Almond Milk"
    assert result["brands"] == "Silk"
    assert result["barcode"] == "0018627"
    mock_get.assert_called_once()


@patch("api.requests.get")
def test_get_product_by_barcode_not_found(mock_get):
    mock_get.return_value = _mock_response({"status": 0})

    with pytest.raises(ExternalAPIError):
        get_product_by_barcode("0000000")


@patch("api.requests.get")
def test_get_product_by_barcode_network_failure(mock_get):
    mock_get.side_effect = requests.ConnectionError("network down")

    with pytest.raises(ExternalAPIError):
        get_product_by_barcode("0018627")


@patch("api.requests.get")
def test_get_product_by_name_success(mock_get):
    mock_get.return_value = _mock_response({
        "products": [
            {
                "code": "9999",
                "product_name": "Peanut Butter",
                "brands": "Jif",
                "ingredients_text": "peanuts, salt",
                "categories": "spreads",
                "image_url": None,
            }
        ]
    })

    result = get_product_by_name("peanut butter")

    assert result["product_name"] == "Peanut Butter"
    assert result["brands"] == "Jif"


@patch("api.requests.get")
def test_get_product_by_name_no_results(mock_get):
    mock_get.return_value = _mock_response({"products": []})

    with pytest.raises(ExternalAPIError):
        get_product_by_name("nonexistent product xyz")


@patch("api.requests.get")
def test_get_product_by_name_http_error(mock_get):
    mock_get.return_value = _mock_response(
        {}, status_code=500, raise_for_status_error=requests.HTTPError("server error")
    )

    with pytest.raises(ExternalAPIError):
        get_product_by_name("anything")


@patch("api.requests.get")
def test_barcode_lookup_sends_required_user_agent(mock_get):
    """OpenFoodFacts asks all integrations to send a custom User-Agent."""
    mock_get.return_value = _mock_response({
        "status": 1, "product": {"code": "123", "product_name": "X"}
    })

    get_product_by_barcode("123")

    _, kwargs = mock_get.call_args
    assert "headers" in kwargs
    assert "User-Agent" in kwargs["headers"]
    assert kwargs["headers"]["User-Agent"] != ""


@patch("api.requests.get")
def test_name_search_sends_required_user_agent(mock_get):
    mock_get.return_value = _mock_response({
        "products": [{"code": "9", "product_name": "Y"}]
    })

    get_product_by_name("y")

    _, kwargs = mock_get.call_args
    assert "headers" in kwargs
    assert "User-Agent" in kwargs["headers"]


@patch("api.requests.get")
def test_barcode_lookup_uses_v3_endpoint(mock_get):
    """v3 is the current recommended API version for product reads."""
    mock_get.return_value = _mock_response({
        "status": 1, "product": {"code": "123", "product_name": "X"}
    })

    get_product_by_barcode("123")

    args, _ = mock_get.call_args
    assert "/api/v3/product/123.json" in args[0]


@patch("api.requests.get")
def test_normalize_product_handles_missing_fields(mock_get):
    """Products with sparse data shouldn't crash the normalizer."""
    mock_get.return_value = _mock_response({
        "status": 1,
        "product": {"code": "123"}  
    })

    result = get_product_by_barcode("123")
    assert result["product_name"] == "Unknown product"
    assert result["brands"] == ""
