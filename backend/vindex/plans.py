"""Public, server-owned plan catalogue. Currency selection never grants paid access."""

from datetime import UTC, datetime
from typing import Literal

from babel.numbers import get_currency_precision, get_territory_currencies
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["Plans"])
PRICE_VERSION = "2026-11-07.1"
# Fixed regional launch prices in minor units, not a live FX conversion or processor IDs.
PLUS_MONTHLY = {
    "USD": 600,
    "INR": 39900,
    "EUR": 600,
    "GBP": 500,
    "CAD": 800,
    "AUD": 900,
    "NZD": 1000,
    "SGD": 800,
    "AED": 2200,
    "JPY": 900,
    "BRL": 2900,
    "MXN": 9900,
    "CHF": 600,
}


class PlanOut(BaseModel):
    id: Literal["free", "plus"]
    name: str
    amount_minor: int
    currency: str
    currency_exponent: int
    interval: Literal["month"]
    availability: Literal["available", "coming_soon"]
    features: list[str]


class PlansOut(BaseModel):
    country: str | None
    local_currencies: list[str]
    local_currency_available: bool
    currency: str
    currency_selection_required: bool
    price_version: str
    pricing_basis: Literal["fixed_regional"]
    taxes_included: bool
    notice: str | None
    paid_checkout_available: bool
    plans: list[PlanOut]


@router.get("/plans", response_model=PlansOut)
def plans(country: str | None = Query(None, pattern=r"^[A-Za-z]{2}$")):
    code = country.upper() if country else None
    local = get_territory_currencies(code, start_date=datetime.now(UTC).date()) if code else []
    if code and not local:
        raise HTTPException(422, "Choose a country with a supported country code")
    matching = [currency for currency in local if currency in PLUS_MONTHLY]
    currency = matching[0] if matching else "USD"
    notice = None
    if not code:
        notice = "Select your country to see available local pricing. Prices are shown in USD."
    elif not matching:
        notice = (
            "Local-currency pricing is not available for this country. Prices are shown in USD."
        )
    common = {
        "currency": currency,
        "currency_exponent": get_currency_precision(currency),
        "interval": "month",
    }
    return {
        "country": code,
        "local_currencies": local,
        "local_currency_available": bool(matching),
        "currency": currency,
        "currency_selection_required": code is None,
        "price_version": PRICE_VERSION,
        "pricing_basis": "fixed_regional",
        "taxes_included": False,
        "notice": notice,
        # No processor is connected. A query parameter or environment switch must
        # never pretend to create a checkout session or a subscription.
        "paid_checkout_available": False,
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "amount_minor": 0,
                "availability": "available",
                "features": [
                    "Search jobs and open original applications",
                    "Save a profile and resume when accounts are available",
                    "Get recommendations with readable reasons",
                ],
                **common,
            },
            {
                "id": "plus",
                "name": "Plus",
                "amount_minor": PLUS_MONTHLY[currency],
                "availability": "coming_soon",
                # Premium feature/entitlement activation belongs to the real
                # billing integration. No unimplemented feature is sold here.
                "features": ["Paid membership is not available yet"],
                **common,
            },
        ],
    }
