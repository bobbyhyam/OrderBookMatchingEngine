from datetime import datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from order_matching.api.models.requests import PlaceRequest


def test_match_with_openapi_examples(client: TestClient) -> None:
    for example in PlaceRequest.model_json_schema()["openapi_examples"].values():
        response = client.post("/place", json=example["value"])
        assert response.status_code == 200


def test_place_single_limit_order_success(client: TestClient, *, sample_limit_order: dict[str, Any]) -> None:
    response = client.post("/place", json={"orders": [sample_limit_order]})
    assert response.status_code == 200
    data = response.json()
    assert "Successfully placed" in data["message"]
    assert len(data["orders"]) == 1
    placed = data["orders"][0]
    assert placed["order_id"] == sample_limit_order["order_id"]
    assert placed["side"] == sample_limit_order["side"]
    assert placed["price"] == sample_limit_order["price"]
    assert placed["size"] == sample_limit_order["size"]
    assert placed["execution"] == "LIMIT"
    assert placed["status"] == "OPEN"


def test_place_batch_orders_success(
    client: TestClient, *, sample_limit_order: dict[str, Any], sample_market_order: dict[str, Any]
) -> None:
    # Alter IDs to make them unique
    sample_market_order["order_id"] = "order_market"
    response = client.post("/place", json={"orders": [sample_limit_order, sample_market_order]})
    assert response.status_code == 200
    data = response.json()
    assert "Successfully placed 2 orders" in data["message"]
    assert len(data["orders"]) == 2

    # Verify that no trades were executed upon placement
    trades_response = client.get("/trades")
    assert trades_response.status_code == 200
    assert trades_response.json()["trades"] == []


def test_place_market_order_success(client: TestClient, *, sample_market_order: dict[str, Any]) -> None:
    response = client.post("/place", json={"orders": [sample_market_order]})
    assert response.status_code == 200
    data = response.json()
    assert len(data["orders"]) == 1
    placed = data["orders"][0]
    assert placed["order_id"] == sample_market_order["order_id"]
    assert placed["execution"] == "MARKET"


def test_place_duplicate_order_id_rejection(client: TestClient, *, sample_limit_order: dict[str, Any]) -> None:
    # Place it once
    response = client.post("/place", json={"orders": [sample_limit_order]})
    assert response.status_code == 200

    # Place again with same ID
    response = client.post("/place", json={"orders": [sample_limit_order]})
    assert response.status_code == 400
    assert "Duplicate order ID" in response.json()["detail"]


def test_place_duplicate_order_id_in_same_request(client: TestClient, *, sample_limit_order: dict[str, Any]) -> None:
    response = client.post("/place", json={"orders": [sample_limit_order, sample_limit_order]})
    assert response.status_code == 400
    assert "Duplicate order ID" in response.json()["detail"]


def test_place_invalid_order_type_rejection(client: TestClient, *, sample_limit_order: dict[str, Any]) -> None:
    invalid_order = sample_limit_order.copy()
    invalid_order["order_type"] = "invalid_type"
    response = client.post("/place", json={"orders": [invalid_order]})
    assert response.status_code == 422


def test_place_negative_size_rejection(client: TestClient, *, sample_limit_order: dict[str, Any]) -> None:
    invalid_order = sample_limit_order.copy()
    invalid_order["size"] = -1.0
    response = client.post("/place", json={"orders": [invalid_order]})
    assert response.status_code == 422


def test_place_zero_size_rejection(client: TestClient, *, sample_limit_order: dict[str, Any]) -> None:
    invalid_order = sample_limit_order.copy()
    invalid_order["size"] = 0.0
    response = client.post("/place", json={"orders": [invalid_order]})
    assert response.status_code == 422


def test_place_missing_required_fields_rejection(client: TestClient, *, sample_limit_order: dict[str, Any]) -> None:
    invalid_order = sample_limit_order.copy()
    del invalid_order["trader_id"]
    response = client.post("/place", json={"orders": [invalid_order]})
    assert response.status_code == 422


def test_place_market_order_with_price_rejection(client: TestClient, *, sample_market_order: dict[str, Any]) -> None:
    # Market orders should forbid price field (extra="forbid")
    invalid_order = sample_market_order.copy()
    invalid_order["price"] = 100.0
    response = client.post("/place", json={"orders": [invalid_order]})
    assert response.status_code == 422


def _limit_order(*, order_id: str, side: str, price: float, timestamp: str) -> dict[str, Any]:
    return {
        "order_type": "limit",
        "order_id": order_id,
        "trader_id": f"{order_id}-trader",
        "side": side,
        "size": 1.0,
        "price": price,
        "timestamp": timestamp,
    }


def test_place_preserves_non_crossing_tick_aligned_prices(client: TestClient, *, sample_timestamp: datetime) -> None:
    timestamp = sample_timestamp.isoformat()
    orders = [
        _limit_order(order_id="sell", side="SELL", price=100.04, timestamp=timestamp),
        _limit_order(order_id="buy", side="BUY", price=100.01, timestamp=timestamp),
    ]
    response = client.post("/place", json={"orders": orders})
    assert response.status_code == 200
    assert [o["price"] for o in response.json()["orders"]] == [100.04, 100.01]

    match_response = client.post("/match", json={"timestamp": timestamp})
    assert match_response.status_code == 200
    assert match_response.json()["trades"] == []


def test_place_small_positive_price_is_not_converted_to_zero(client: TestClient, *, sample_timestamp: datetime) -> None:
    timestamp = sample_timestamp.isoformat()
    orders = [
        _limit_order(order_id="sell", side="SELL", price=0.01, timestamp=timestamp),
        _limit_order(order_id="buy", side="BUY", price=0.01, timestamp=timestamp),
    ]
    response = client.post("/place", json={"orders": orders})
    assert response.status_code == 200
    assert [o["price"] for o in response.json()["orders"]] == [0.01, 0.01]

    trades = client.post("/match", json={"timestamp": timestamp}).json()["trades"]
    assert len(trades) == 1
    assert trades[0]["price"] == 0.01


@pytest.mark.parametrize("price", [100.041, 100.005, 0.001, 0.009, 1e-05])
def test_place_off_tick_price_rejection(
    client: TestClient, *, sample_limit_order: dict[str, Any], price: float
) -> None:
    valid_order = sample_limit_order.copy()
    valid_order["order_id"] = "valid"
    invalid_order = sample_limit_order.copy()
    invalid_order["price"] = price
    response = client.post("/place", json={"orders": [valid_order, invalid_order]})
    assert response.status_code == 422

    order_book = client.get("/orders").json()
    assert order_book["bids"] == {}
    assert order_book["offers"] == {}


@pytest.mark.parametrize("price", [0.01, 0.1, 1.0, 99.99, 100.5, 12345.67])
def test_place_tick_aligned_price_success(
    client: TestClient, *, sample_limit_order: dict[str, Any], price: float
) -> None:
    order = sample_limit_order.copy()
    order["price"] = price
    response = client.post("/place", json={"orders": [order]})
    assert response.status_code == 200
    assert response.json()["orders"][0]["price"] == price
