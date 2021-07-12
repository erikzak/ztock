# -*- coding: utf-8 -*-
"""
Base Market class.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Union

from ..candlestick import Candlestick
from ..clients import Client
from ..symbol import Symbol


class Market(Client):
    """
    Base Market class, subclasses handle requests to market data vendors.
    """
    name = "Market"

    def refresh(self):
        """Refreshes client connection."""
        raise NotImplementedError("Market.refresh() not implemented")

    def list_symbols(
            self, exchange_codes: Union[List[str], str], symbol_type: Optional[str] = None
    ) -> Dict[str, Symbol]:
        """
        Lists symbols for given exchange codes. Returns list of Symbol
        objects.

        :param exchange_codes: exchange codes, e.g. 'OL', 'US'
        :type exchange_codes: list of str or str
        :param symbol_type: OpenFIGI symbol type, e.g. "Common Stock"
        :type symbol_type: str
        :returns: symbols for given exchanges
        :rtype: dict of (str, ztock.broker.Symbol)
        """
        raise NotImplementedError("Market.list_symbols() not implemented")

    def lookup_symbol(self, symbol_name: str) -> Symbol:
        """
        Searches for a given symbol, returns best match.

        :param symbol_name: symbol to search for
        :type symbol_name: str
        :return: symbol object
        :rtype: ztock.broker.Symbol
        """
        raise NotImplementedError("Market.lookup_symbol() not implemented")

    def get_symbol_quote(
            self,
            symbol: Symbol,
            price_type: str = None
    ) -> Decimal:
        """
        Returns current price for symbol.

        :param symbol: symbol to get quote for
        :type symbol: ztock.Symbol
        :param price_type: "bid", "mid" or "ask" price. Defaults to "ask"
        :type price_type: str
        :return: current symbol price
        :rtype: decimal.Decimal
        """
        raise NotImplementedError("Market.get_symbol_quote() not implemented")

    def get_candlesticks(
            self,
            symbol: Symbol,
            resolution: Union[str, int] = None,
            intervals: int = None
    ) -> List[Candlestick]:
        """
        Fetches symbol candlesticks.

        :param symbol: symbol object
        :type symbol: ztock.broker.Symbol
        :param resolution: candlestick interval, defaults to 5 minutes
        :type resolution: int or str
        :param intervals: number of intervals to fetch, defaults to 50
        :type intervals: int
        :returns: list of candlestick objects
        :rtype: list of ztock.Candlestick
        """
        raise NotImplementedError("Market.get_candlesticks() not implemented")

    def get_average_price(
            self,
            symbol: Symbol,
            operation: str,
            days: int = None
    ) -> Dict[str, Union[int, Decimal]]:
        """
        Fetches average order buy or sell price for the given number of
        previous days.

        Returns a dict containing average buy/sell price and total volume as
        "average_price" and "volume" key-value pairs.

        :param symbol: symbol the get average price for
        :type symbol: ztock.broker.Symbol
        :param operation: order operation, 'BUY' or 'SELL'
        :type operation: str
        :param days: number of days to fetch orders for. Defaults to 7
        :type days: int
        :return: order history with average price and volume
        :rtype: dict of (str, [int, Decimal])
        """
        days = days or 7
        raise NotImplementedError("Market.get_average_price() not implemented")
