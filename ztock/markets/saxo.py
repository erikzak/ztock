# -*- coding: utf-8 -*-
"""
Saxo Bank market data handler.

https://www.developer.saxo
"""
from decimal import Decimal
from typing import Dict, List, Optional, Union

from ..candlestick import Candlestick
from ..clients.saxo import SaxoClient
from ..exceptions import NoDataException
from ..symbol import Symbol
from ..utils import generate_random_string, parse_decimal


EXCHANGE_REMAP = {

}


class SaxoMarket(SaxoClient):
    """
    Saxo Market subclass.
    """
    name = "SaxoMarket"
    security_type_remap = {
        "Common Stock": "Stock",
    }
    _symbols = {}

    def list_symbols(
            self, exchange_codes: Union[List[str], str],
            symbol_type: Optional[str] = None, mic_codes: Optional[Union[List[str], str]] = None,
            account_key: Optional[str] = None, include_non_tradeable: Optional[bool] = False
    ) -> Dict[str, Symbol]:
        """
        Lists symbols for given exchange codes. Returns list of Symbol
        objects.

        https://www.developer.saxo/openapi/referencedocs/ref/v1/instruments/getsummaries/6e8602a4943e270d01ada208c8b26770

        :param exchange_codes: exchange codes, e.g. 'OL', 'US'
        :type exchange_codes: list of str or str
        :param symbol_type: OpenFIGI symbol type, e.g. "Common Stock"
        :type symbol_type: str
        :param mic_codes: optional list of MIC codes
        :type mic_codes: list of str or str
        :param account_key: optional Saxo Bank account key. Limits results to
            what account has access to
        :type account_key: str
        :param include_non_tradeable: optional flag for including symbols not
            tradeable through online client
        :type include_non_tradeable: bool
        :return: symbols for given exchanges
        :rtype: dict of (str, ztock.broker.Symbol)
        """
        if (isinstance(exchange_codes, str)):
            exchange_codes = [exchange_codes]
        symbol_type = self.security_type_remap.get(symbol_type, symbol_type)
        # Define URL
        url = f"{self.root_url}/ref/v1/instruments"

        symbols = {}
        for exchange_code in exchange_codes:
            exchange_code = EXCHANGE_REMAP.get(exchange_code, exchange_code)
            # Check if cached list exists
            if (
                    exchange_code in self._symbols and (
                        (symbol_type is None and "All" in self._symbols[exchange_code])
                        or symbol_type in self._symbols[exchange_code]
                    )
            ):
                symbols.update(self._symbols[exchange_code][symbol_type or "All"])
                continue
            # Generate and send request with payload
            params = {
                "$top": 500,
                "ExchangeId": exchange_code,
                "IncludeNonTradable": include_non_tradeable,
            }
            if (symbol_type):
                params["AssetTypes"] = self.security_type_remap.get(symbol_type, symbol_type)
            if (account_key):
                params["AccountKey"] = account_key
            response = self.request("GET", url, data=params)
            # Unpack result and add Symbols to dict
            result = response.json()
            exchange_symbols = {}
            for symbol_dict in result["Data"]:
                symbol = self._unpack_symbol(symbol_dict)
                exchange_symbols[symbol.name] = symbol
            while (result.get("__next", None)):
                result = self.request("GET", result["__next"]).json()
                for symbol_dict in result["Data"]:
                    symbol = self._unpack_symbol(symbol_dict)
                    exchange_symbols[symbol.name] = symbol
            symbols.update(exchange_symbols)
            # Cache symbols per exchange per symbol type
            if (exchange_code not in self._symbols):
                self._symbols[exchange_code] = {}
            self._symbols[exchange_code][symbol_type or "All"] = exchange_symbols
        return symbols

    def get_symbol_quote(
            self,
            symbol: Symbol,
            price_type: str = None
    ) -> Decimal:
        """
        Returns current price for symbol.

        https://www.developer.saxo/openapi/referencedocs/trade/v1/infoprices/getinfopriceasync/eee3cc82474270ca79836aa7d8b1e923

        :param symbol: symbol to get quote for
        :type symbol: ztock.Symbol
        :param price_type: "bid", "mid" or "ask" price. Defaults to "ask"
        :type price_type: str
        :return: current symbol price
        :rtype: decimal.Decimal
        """
        price_type = price_type or "Ask"
        # Get Saxo symbol details if no symbol.Identifier
        if (not hasattr(symbol, "Identifier")):
            symbol = self.lookup_symbol(symbol.name)
        # Define URL and params
        url = f"{self.root_url}/trade/v1/infoprices"
        params = {
            "AssetType": symbol.AssetType,
            "Uic": symbol.Identifier,
            "QuoteCurrency": False,
        }
        # Generate and send request with payload
        response = self.request("GET", url, data=params)
        # Unpack result
        result = response.json()
        quote = result["Quote"]
        price_type = price_type.title()
        # Check if price data is available
        if (price_type not in quote or quote.get("PriceTypeAsk", None) == "NoAccess"):
            raise NoDataException(
                f"{self.name} - No quote data returned for symbol {symbol.name}: {quote}"
            )
        # Debug log quote and return requested price
        amount = quote.get("Amount", 1) or 1
        price = parse_decimal(quote[price_type]) / amount
        self.logger.debug("{} - {} quote: {}".format(self.name, symbol.name, quote))
        return price

    def get_candlesticks_sub(
            self,
            symbol: Symbol,
            resolution: Union[str, int] = None,
            intervals: int = None,
            price_type: str = None
    ) -> List[Candlestick]:
        """
        Fetches symbol candlesticks.

        https://www.developer.saxo/openapi/referencedocs/chart/v1/charts/addsubscriptionasync/ffe4364c2a06b804b58ce27ad5c8d521

        :param symbol: symbol object
        :type symbol: ztock.broker.Symbol
        :param resolution: candlestick interval, defaults to 5 minutes
        :type resolution: int or str
        :param intervals: number of intervals to fetch, defaults to 50
        :type intervals: int
        :param price_type: "bid", "ask" or "mid", defaults to "ask"
        :type price_type: str
        :returns: list of candlestick objects
        :rtype: list of ztock.Candlestick
        """
        candlesticks = []
        price_type = price_type.title() if (price_type is not None) else "Ask"

        # Define URL and parameters
        url = f"{self.root_url}/chart/v1/charts/subscriptions"
        resolution = resolution or 5
        intervals = intervals or 50

        # Remap string-based resolutions
        if (resolution == "D"):
            resolution = 1440
        elif (resolution == "W"):
            resolution = 10080
        elif (resolution == "M"):
            resolution = 43200

        # Get Saxo symbol details if no symbol.Identifier
        if (not hasattr(symbol, "Identifier")):
            symbol = self.lookup_symbol(symbol.name)

        # Generate payload and send request
        context_id = generate_random_string(8)
        reference_id = generate_random_string(8)
        params = {
            "Format": "application/json",
            "Arguments": {
                "Count": intervals,
                "FieldGroups": ["ChartInfo", "Data"],
                "Horizon": resolution,
                "Uic": symbol.Identifier,
                "AssetType": getattr(symbol, "AssetType", None) or "Stock"
            },
            "RefreshRate": 10000,
            "ContextId": context_id,
            "ReferenceId": reference_id,
        }
        self.logger.debug(
            "{} - Fetching candlesticks using POST request params: {}".format(self.name, params)
        )
        response = self.request("POST", url, data=params)

        # Unpack response, validate status and generate candlesticks
        result = response.json()
        snapshot = result["Snapshot"]
        self.logger.debug("{} - Candlestick info: {}".format(self.name, snapshot["ChartInfo"]))
        data = snapshot["Data"]
        for candlestick in data:
            open_ = candlestick.get(f"Open{price_type}", candlestick.get("Open", None))
            high = candlestick.get(f"High{price_type}", candlestick.get("High", None))
            low = candlestick.get(f"Low{price_type}", candlestick.get("Low", None))
            close = candlestick.get(f"Close{price_type}", candlestick.get("Close", None))
            volume = candlestick.get("Volume", None)
            timestamp = self._parse_utc_datestring(candlestick["Time"])
            candlesticks.append(Candlestick(open_, high, low, close, volume, timestamp))

        # Cancel subscription instantly
        delete_url = f"{self.root_url}/chart/v1/charts/subscriptions/{context_id}/{reference_id}"
        self.request("DELETE", delete_url)
        return candlesticks

    def get_candlesticks(
            self,
            symbol: Symbol,
            resolution: Union[str, int] = None,
            intervals: int = None,
            price_type: str = None
    ) -> List[Candlestick]:
        """
        Fetches symbol candlesticks.

        https://www.developer.saxo/openapi/referencedocs/chart/v1/charts

        :param symbol: symbol object
        :type symbol: ztock.broker.Symbol
        :param resolution: candlestick interval, defaults to 5 minutes
        :type resolution: int or str
        :param intervals: number of intervals to fetch, defaults to 50
        :type intervals: int
        :param price_type: "bid", "ask" or "mid", defaults to "ask"
        :type price_type: str
        :returns: list of candlestick objects
        :rtype: list of ztock.Candlestick
        """
        candlesticks = []
        price_type = price_type.title() if (price_type is not None) else "Ask"

        # Define URL and parameters
        url = f"{self.root_url}/chart/v1/charts"
        resolution = resolution or 5
        intervals = intervals or 50

        # Remap string-based resolutions
        if (resolution == "D"):
            resolution = 1440
        elif (resolution == "W"):
            resolution = 10080
        elif (resolution == "M"):
            resolution = 43200

        # Get Saxo symbol details if no symbol.Identifier
        if (not hasattr(symbol, "Identifier")):
            symbol = self.lookup_symbol(symbol.name)

        # Generate payload and send request
        params = {
            "AssetType": getattr(symbol, "AssetType", None) or "Stock",
            "Count": intervals,
            "Horizon": resolution,
            "Uic": symbol.Identifier,
            "FieldGroups": "ChartInfo,Data",
        }
        self.logger.debug(
            "{} - Fetching candlesticks using request params: {}".format(self.name, params)
        )
        response = self.request("GET", url, data=params)

        # Unpack response, validate status and generate candlesticks
        result = response.json()
        self.logger.debug("{} - Candlestick info: {}".format(self.name, result["ChartInfo"]))
        data = result["Data"]
        try:
            for candlestick in data:
                open_ = candlestick.get(f"Open{price_type}", candlestick.get("Open", None))
                high = candlestick.get(f"High{price_type}", candlestick.get("High", None))
                low = candlestick.get(f"Low{price_type}", candlestick.get("Low", None))
                close = candlestick.get(f"Close{price_type}", candlestick.get("Close", None))
                volume = candlestick.get("Volume", None)
                timestamp = self._parse_utc_datestring(candlestick["Time"])
                candlesticks.append(Candlestick(open_, high, low, close, volume, timestamp))
        except Exception:
            self.logger.error("{} - Unable to unpack candlesticks: {}".format(self.name, data))
            raise
        return candlesticks

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
        # Get candlesticks
        days = days or 7
        price_type = "bid" if (operation.upper() == "SELL") else "ask"
        candlesticks = self.get_candlesticks(symbol, "D", days, price_type=price_type)
        # Sum prices and volumes
        total_price = parse_decimal(0)
        volume = 0
        for candlestick in candlesticks:
            total_price += candlestick.close
            if (candlestick.volume):
                volume += candlestick.volume
        order_history = {
            "average_price": total_price / len(candlesticks),
            "volume": volume or None,
        }
        return order_history
