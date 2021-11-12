# -*- coding: utf-8 -*-
"""
Interactive Brokers (IBKR) Market class.

Fetches market data from IBKR.

WORK IN PROGRESS, NEVER GOT IBKR MARKET DATA TO WORK..
"""
import urllib3
from decimal import Decimal
from typing import Dict, List, Optional, Union

from .market import Market
from ..brokers.ibkr import IBKR as IBKRBroker
from ..candlestick import Candlestick
from ..config import Config
from ..symbol import Symbol
from ..utils import parse_decimal


class IBKR(Market):
    """
    IBKR Market subclass.
    """
    name = "IBKRMarket"
    timeout = 60
    retry_on_status_codes = [500]

    version = "v1"

    def __init__(self, config: Config) -> None:
        """
        Inits IBKR market object using supplied config.

        The following config key-value pairs need to be defined:

        * gateway_url: optional address to IBKR gateway, defaults to localhost
        * gateway_port: optional port used for IBKR gateway, defaults to 5000

        :param config: market config
        :type config: Config
        """
        self.config = config
        gateway_url = getattr(config, "gateway_url", "localhost")
        gateway_port = getattr(config, "gateway_port", 5000)
        self.root_url = f"https://{gateway_url}:{gateway_port}/{self.version}/api"

        # Disable localhost SSL warning
        urllib3.disable_warnings()

        # Query endpoints relevant for subsequent queries
        IBKRBroker.get_portfolio_accounts(self)
        return

    def authenticate(self):
        """Authentication happens through IBKR gateway software, this does nothing."""
        return

    def refresh(self):
        """Same as authenticate()."""
        return

    def list_symbols(
            self, exchange_codes: Union[List[str], str],
            symbol_type: Optional[str] = None, mic_codes: Optional[Union[List[str], str]] = None
    ) -> Dict[str, Symbol]:
        """
        NOT IMPLEMENTED, IBKR DOES NOT HAVE THIS FUNCTIONALITY.

        Lists symbols for given exchange codes. Returns list of Symbol
        objects.

        :param exchange_codes: exchange codes, e.g. 'OL', 'US'
        :type exchange_codes: list of str or str
        :param symbol_type: OpenFIGI symbol type, e.g. "Common Stock"
        :type symbol_type: str
        :param mic_codes: optional list of MIC codes
        :type mic_codes: list of str or str
        :returns: symbols for given exchanges
        :rtype: dict of (str, ztock.broker.Symbol)
        """
        raise NotImplementedError("IBKR.list_symbols() not implemented")

    def lookup_symbol(self, symbol_name: str, contract_type: Optional[str] = None) -> Symbol:
        """
        Searches for a given symbol, returns best match.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Contract/paths/~1iserver~1secdef~1search/post

        :param symbol_name: symbol to search for
        :type symbol_name: str
        :param contract_type: optional IBKR contract type, defaults to STK
        :type contract_type: str
        :return: symbol object
        :rtype: ztock.broker.Symbol
        """
        contract_type = contract_type or "STK"
        # Define URL
        url = f"{self.root_url}/iserver/secdef/search"
        # Query API
        data = {
            "symbol": symbol_name,
        }
        response = self.request("POST", url, json=data)
        # Unpack response
        contracts = response.json()
        # Get symbol contract info
        for contract_info in contracts:
            if (contract_info["symbol"] != symbol_name):
                continue
            for section in contract_info["sections"]:
                if (section.get("symbol", symbol_name) != symbol_name):
                    continue
                if (section["secType"] == contract_type):
                    symbol = Symbol(
                        contracts[0]["symbol"],
                        **{**contract_info, **section}
                    )
                    return symbol
        # If no contract found, raise error
        raise ValueError("IBKR - No {} contract found for symbol: {}".format(
            contract_type, symbol_name
        ))

    def get_symbol_quote(
            self,
            symbol: Symbol,
            price_type: str = None
    ) -> Decimal:
        """
        Returns current price for symbol.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Market-Data/paths/~1iserver~1marketdata~1snapshot/get

        :param symbol: symbol to get quote for
        :type symbol: ztock.Symbol
        :param price_type: "bid", "mid" or "ask" price. Defaults to "ask"
        :type price_type: str
        :return: current symbol price
        :rtype: decimal.Decimal
        """
        # Check if Symbol has contract id. If not, lookup symbol name
        if (getattr(symbol, "conid", None) is None):
            symbol = self.lookup_symbol(symbol.name)

        # Define URL
        url = f"{self.root_url}/iserver/marketdata/snapshot"
        # Query API
        contract_id = symbol.conid
        last_price_field = "31"
        data = {
            "conids": contract_id,
            "fields": last_price_field,
        }
        response = self.request("GET", url, data=data)
        # Unpack response
        results = response.json()
        last_price = parse_decimal(results[0][last_price_field])
        return last_price

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
