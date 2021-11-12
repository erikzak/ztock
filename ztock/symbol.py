# -*- coding: utf-8 -*-
"""
Base Symbol class. Unifies and keeps track of symbol parameters across brokers
and market data vendors.
"""


class Symbol:
    """Base Symbol class."""
    def __init__(self, name: str, **kwargs):
        """
        Inits Symbol object with defined name and optional keyword arguments.

        Common keyword parameters:

        * currency: symbol currency code, e.g. USD
        * description: free-text company/ticker description
        * display_symbol:
        * exchange: symbol exchange code, e.g. US, OL
        * mic: ISO MIC code
        * figi
        * type: symbol type, e.g. Common Stock

        :param name: symbol name
        :type name: str
        """
        self.type = None
        self.currency = None
        self.description = None
        self.display_symbol = None
        self.exchange = None
        self.mic = None
        self.figi = None

        self.name = name
        for key, value in kwargs.items():
            if (getattr(self, key, None) is None):
                setattr(self, key, value)
        return

    def __repr__(self) -> str:
        """Prints symbol name along with exchange, if defined."""
        return f"{self.name} {vars(self)})"

    def __str__(self) -> str:
        """See __repr__"""
        return self.__repr__()
