# -*- coding: utf-8 -*-
"""
Base Symbol class. Unifies and keeps track of symbol parameters across brokers
and market data vendors.
"""


class Symbol:
    """Base Symbol class."""
    exchange = None

    def __init__(self, name: str, **kwargs):
        """
        Inits Symbol object with defined name and optional keyword arguments.

        Common keyword parameters:

        * currency: symbol currency code, e.g. USD
        * description: free-text company/ticker description
        * display_symbol:
        * exchange: symbol exchange code, e.g. US, OL
        * type: symbol type, e.g. Common Stock
        * figi
        * mic

        :param name: symbol name
        :type name: str
        """
        self.name = name
        for key, value in kwargs.items():
            if (not hasattr(self, key)):
                setattr(self, key, value)
        return

    def __repr__(self) -> str:
        """Prints symbol name along with exchange, if defined."""
        return f"{self.name} {vars(self)})"

    def __str__(self) -> str:
        """See __repr__"""
        return self.__repr__()
