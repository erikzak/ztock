# -*- coding: utf-8 -*-
"""
Standardizes broker communication and features like order and symbol
parameters across vendors.
"""
from typing import Any, Dict

from .broker import Broker
from .ibkr import IBKR
from .order import Order
from .position import Position
from .saxo import SaxoBroker


def init_broker(broker_config: Dict[str, Any]) -> Broker:
    """
    Inits Broker object based on configured vendor.

    :param broker_config: broker config
    :type broker_config: Config
    """
    vendor = broker_config.vendor
    vendor_lc = vendor.lower()
    if (vendor_lc == "ibkr"):
        broker = IBKR(broker_config)
    elif (vendor_lc == "saxo"):
        broker = SaxoBroker(broker_config)
    else:
        raise ValueError(f"Unknown broker: {vendor}")
    return broker


__all__ = [
    "Broker",
    "IBKR",
    "Order",
    "Position",
    "init_broker",
]
