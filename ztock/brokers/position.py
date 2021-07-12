# -*- coding: utf-8 -*-
"""
Base Position class. Unifies and keeps track of open trade parameters across
brokers.
"""
from decimal import Decimal
from typing import Optional, Union

from ..symbol import Symbol


class Position:
    """Base Position class."""
    def __init__(
            self,
            id: Union[str, int],
            symbol: str,
            quantity: Union[Decimal, int],
            market_value: Decimal,
            pnl: Decimal = None,
            currency: Optional[str] = None,
            exchange_rate: Optional[Decimal] = None,
            **kwargs
    ) -> None:
        """
        Inits Position object with optional keyword arguments.

        :param id: position id, will vary by broker
        :type id: str or int
        :param symbol: position symbol name
        :type symbol: str
        :param quantity: symbol quantity
        :type quantity: Decimal or int
        :param market_value: current market value
        :type market_value: Decimal
        :param pnl: profit and loss
        :type pnl: Decimal
        :param currency: position currency
        :type currency: str
        :param exchange_rate: optional exchange rate to account currency
        :type exchange_rate: Decimal
        """
        self.id = id
        self.symbol = Symbol(symbol)
        self.quantity = quantity
        self.market_value = market_value
        self.pnl = pnl
        self.currency = currency
        self.exchange_rate = exchange_rate
        for key, value in kwargs.items():
            if (not hasattr(self, key)):
                setattr(self, key, value)
        return

    def __repr__(self) -> str:
        """Prints position id along with available attributes."""
        return f"{vars(self)})"

    def __str__(self) -> str:
        """See __repr__"""
        return self.__repr__()
