# -*- coding: utf-8 -*-
"""
Standardizes market data communication between vendors.
"""
from typing import Any, Dict

from .finnhub import FinnhubMarket
from .market import Market
from .saxo import SaxoMarket


def init_market(market_config: Dict[str, Any]) -> Market:
    """
    Inits Market object based on configured vendor.

    :param market_config: market data config
    :type market_config: Config
    """
    vendor = market_config.vendor
    vendor_lc = vendor.lower()
    if (vendor_lc == "finnhub"):
        market = FinnhubMarket(market_config)
    elif (vendor_lc == "saxo"):
        market = SaxoMarket(market_config)
    else:
        raise ValueError(f"Unknown market data vendor: {vendor}")
    return market


__all__ = [
    "FinnhubMarket",
    "Market",
    "init_market",
    "SaxoMarket",
]
