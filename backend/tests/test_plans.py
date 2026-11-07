"""Real country/currency catalogue, correct units and no fictitious paid activation."""

import pytest
from fastapi.testclient import TestClient
from vindex.api import app

client = TestClient(app)


@pytest.mark.parametrize(
    ("country", "currency", "amount", "exponent"),
    [
        ("IN", "INR", 39900, 2),
        ("US", "USD", 600, 2),
        ("GB", "GBP", 500, 2),
        ("DE", "EUR", 600, 2),
        ("FR", "EUR", 600, 2),
        ("JP", "JPY", 900, 0),
        ("CA", "CAD", 800, 2),
        ("AU", "AUD", 900, 2),
        ("SG", "SGD", 800, 2),
        ("AE", "AED", 2200, 2),
        ("BR", "BRL", 2900, 2),
        ("MX", "MXN", 9900, 2),
        ("NZ", "NZD", 1000, 2),
        ("CH", "CHF", 600, 2),
    ],
)
def test_local_prices(country, currency, amount, exponent):
    response = client.get("/api/v1/plans", params={"country": country})
    assert response.status_code == 200
    data = response.json()
    assert data["currency"] == currency and data["local_currency_available"]
    assert data["plans"][0]["amount_minor"] == 0
    plus = data["plans"][1]
    assert plus["amount_minor"] == amount and plus["currency_exponent"] == exponent
    assert plus["availability"] == "coming_soon" and not data["paid_checkout_available"]
    assert response.headers["cache-control"] == "no-store"


def test_explicit_default_and_unsupported_currency():
    default = client.get("/api/v1/plans").json()
    assert default["country"] is None and default["currency_selection_required"]
    assert default["currency"] == "USD" and default["notice"]
    unsupported = client.get("/api/v1/plans?country=bh").json()
    assert unsupported["local_currencies"] == ["BHD"]
    assert unsupported["currency"] == "USD" and not unsupported["local_currency_available"]
    assert unsupported["notice"]


@pytest.mark.parametrize("country", ["XX", "ZZ", "123", "<script>", "United States", ""])
def test_invalid_country(country):
    assert client.get("/api/v1/plans", params={"country": country}).status_code == 422


def test_client_cannot_change_price_or_activate_plus(monkeypatch):
    monkeypatch.setenv("BILLING_ENABLED", "true")
    response = client.get("/api/v1/plans?country=IN&amount_minor=1&plan=plus&paid=true")
    assert response.json()["plans"][1]["amount_minor"] == 39900
    assert response.json()["paid_checkout_available"] is False
    assert (
        client.post("/api/v1/billing/checkout", json={"plan": "plus", "paid": True}).status_code
        == 404
    )
