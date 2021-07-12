# -*- coding: utf-8 -*-
"""
Currency and exchange rate related functionality.
"""
import datetime
from decimal import Decimal
from typing import Dict

import requests

from .utils import parse_decimal


EXCHANGE_RATES = {}


def convert_currency(amount: Decimal, base_currency: str, target_currency: str) -> Decimal:
    """Converts an amount from source to target currency."""
    exchange_rate = get_exchange_rate(base_currency, target_currency)
    return amount * exchange_rate


def get_exchange_rate(base_currency: str, target_currency: str) -> Decimal:
    """Gets updated exchange rate for source and target currency."""
    cached_rates = EXCHANGE_RATES.get(base_currency, None)
    if (cached_rates and _days_since_update(cached_rates) < 1):
        return cached_rates[target_currency]

    rates = fetch_exchange_rates(base_currency)
    rates["timestamp"] = datetime.datetime.now()
    EXCHANGE_RATES[base_currency] = rates
    return rates[target_currency]


def fetch_exchange_rates(base_currency: str) -> Dict[str, Decimal]:
    url = f"https://frankfurter.app/latest?from={base_currency}"
    response = requests.get(url)
    response.raise_for_status()
    result = response.json()
    rates = {}
    for currency, rate in result["rates"].items():
        rate = parse_decimal(rate)
        rates[currency] = rate
    return rates


def _days_since_update(cached_rates: Dict[str, Decimal]) -> int:
    timestamp = cached_rates.get("timestamp", None)
    if (timestamp is None):
        return 9999
    days_since_update = (datetime.datetime.now() - timestamp).days
    return days_since_update
