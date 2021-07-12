# -*- coding: utf-8 -*-
"""
Finnhub.io market data handler.

https://finnhub.io
"""
import datetime
import logging
import math
from decimal import Decimal
from typing import Dict, List, Optional, Union

import requests

from .market import Market
from ..candlestick import Candlestick
from ..config import Config
from ..constants import LOG_NAME
from ..exceptions import NoDataException
from ..symbol import Symbol
from ..utils import parse_decimal


EXCHANGES = {
    "AS": "NYSE EURONEXT - EURONEXT AMSTERDAM",
    "AT": "ATHENS EXCHANGE S.A. CASH MARKET",
    "AX": "ASX - ALL MARKETS",
    "BA": "BOLSA DE COMERCIO DE BUENOS AIRES",
    "BC": "BOLSA DE VALORES DE COLOMBIA",
    "BD": "BUDAPEST STOCK EXCHANGE",
    "BE": "BOERSE BERLIN",
    "BK": "STOCK EXCHANGE OF THAILAND",
    "BO": "BSE LTD",
    "BR": "NYSE EURONEXT - EURONEXT BRUSSELS",
    "CN": "CANADIAN NATIONAL STOCK EXCHANGE",
    "CO": "OMX NORDIC EXCHANGE COPENHAGEN A/S",
    "CR": "CARACAS STOCK EXCHANGE",
    "DB": "DUBAI FINANCIAL MARKET",
    "DE": "XETRA",
    "DU": "BOERSE DUESSELDORF",
    "F": "DEUTSCHE BOERSE AG",
    "HE": "NASDAQ OMX HELSINKI LTD",
    "HK": "HONG KONG EXCHANGES AND CLEARING LTD",
    "HM": "HANSEATISCHE WERTPAPIERBOERSE HAMBURG",
    "IC": "NASDAQ OMX ICELAND",
    "IR": "IRISH STOCK EXCHANGE - ALL MARKET",
    "IS": "BORSA ISTANBUL",
    "JK": "INDONESIA STOCK EXCHANGE",
    "JO": "JOHANNESBURG STOCK EXCHANGE",
    "KL": "BURSA MALAYSIA",
    "KQ": "KOREA EXCHANGE (KOSDAQ)",
    "KS": "KOREA EXCHANGE (STOCK MARKET)",
    "L": "LONDON STOCK EXCHANGE",
    "LN": "Euronext London",
    "LS": "NYSE EURONEXT - EURONEXT LISBON",
    "MC": "BOLSA DE MADRID",
    "ME": "MOSCOW EXCHANGE",
    "MI": "Italian Stock Exchange",
    "MU": "BOERSE MUENCHEN",
    "MX": "BOLSA MEXICANA DE VALORES (MEXICAN STOCK EXCHANGE)",
    "NE": "AEQUITAS NEO EXCHANGE",
    "NL": "Nigerian Stock Exchange",
    "NS": "NATIONAL STOCK EXCHANGE OF INDIA",
    "NZ": "NEW ZEALAND EXCHANGE LTD",
    "OL": "OSLO BORS ASA",
    "PA": "NYSE EURONEXT - MARCHE LIBRE PARIS",
    "PM": "Philippine Stock Exchange",
    "PR": "PRAGUE STOCK EXCHANGE",
    "QA": "QATAR EXCHANGE",
    "RG": "NASDAQ OMX RIGA",
    "SA": "Brazil Bolsa - Sao Paolo",
    "SG": "BOERSE STUTTGART",
    "SI": "SINGAPORE EXCHANGE",
    "SN": "SANTIAGO STOCK EXCHANGE",
    "SR": "SAUDI STOCK EXCHANGE",
    "SS": "SHANGHAI STOCK EXCHANGE",
    "ST": "NASDAQ OMX NORDIC STOCKHOLM",
    "SW": "SWISS EXCHANGE",
    "SZ": "SHENZHEN STOCK EXCHANGE",
    "T": "TOKYO STOCK EXCHANGE-TOKYO PRO MARKET",
    "TA": "TEL AVIV STOCK EXCHANGE",
    "TL": "NASDAQ OMX TALLINN",
    "TO": "TORONTO STOCK EXCHANGE",
    "TW": "TAIWAN STOCK EXCHANGE",
    "US": "US exchanges (NYSE, Nasdaq)",
    "V": "TSX VENTURE EXCHANGE - NEX",
    "VI": "Vienna Stock Exchange",
    "VN": "Vietnam exchanges including HOSE, HNX and UPCOM",
    "VS": "NASDAQ OMX VILNIUS",
    "WA": "WARSAW STOCK EXCHANGE/EQUITIES/MAIN MARKET",
    "HA": "Hanover Stock Exchange",
    "SX": "DEUTSCHE BOERSE Stoxx",
    "TG": "	DEUTSCHE BOERSE TradeGate ",
    "SC": "BOERSE_FRANKFURT_ZERTIFIKATE",
}


# Exchange codes to remap
EXCHANGE_REMAP = {
    # US exchanges
    "NASDAQ": "US",
    "NYSE": "US",
    # Oslo Stock Exchange
    "OSE": "OL",
}


class FinnhubMarket(Market):
    """Finnhub Market subclass."""
    name = "FinnhubMarket"
    root_url = "https://finnhub.io/api"
    session = requests.Session()

    def __init__(self, config: Config):
        """
        Inits Finnhub object using supplied config.

        Config must contain the following parameters:
            * api_key

        :param config: market config
        :type config: Config
        """
        self.config = config
        self.api_key = config.api_key
        version = getattr(config, "version", "v1")
        self.api_url = f"{self.root_url}/{version}"

        # Logger
        self.logger = logging.getLogger(LOG_NAME)

        # Authenticate
        self.authenticate()
        return

    def authenticate(self) -> None:
        """
        Authentication with Finnhub API is through a header. This refreshes
        the module requests session and adds the header.
        """
        self.session = requests.Session()
        self.session.headers.update({
            "X-Finnhub-Token": self.api_key
        })
        return

    def refresh(self):
        """Does nothing, no refresh necessary."""
        return

    def list_symbols(
            self, exchange_codes: Union[List[str], str], symbol_type: Optional[str] = None
    ) -> Dict[str, Symbol]:
        """
        Lists symbols for given exchange codes. Returns list of Symbol
        objects.

        https://finnhub.io/docs/api/stock-symbols

        :param exchange_codes: exchange codes, e.g. 'OL', 'US'
        :type exchange_codes: list of str or str
        :param symbol_type: OpenFIGI symbol type, e.g. "Common Stock"
        :type symbol_type: str
        :returns: dict of symbol-Symbol key-valie pairs for given exchange(s)
        :rtype: dict of (str, ztock.broker.Symbol)
        """
        if (isinstance(exchange_codes, str)):
            exchange_codes = [exchange_codes]
        # Define URL
        url = f"{self.api_url}/stock/symbol"

        # Loop through exchanges and get symbols
        symbols = {}
        for exchange_code in exchange_codes:
            # Generate and send request with payload
            params = {
                "exchange": EXCHANGE_REMAP.get(exchange_code, exchange_code),
            }
            if (symbol_type):
                params["securityType"] = symbol_type
            response = self.session.get(url, params=params)
            response.raise_for_status()
            # Unpack result and append Symbols to list
            exchange_symbols = response.json()
            for symbol in exchange_symbols:
                symbol_name = symbol["symbol"]
                symbols[symbol_name] = Symbol(
                    symbol_name,
                    display_symbol=symbol["displaySymbol"],
                    exchange=exchange_code,
                    # Part of kwargs:
                    # currency=symbol["currency"],
                    # description=symbol["description"],
                    # figi=symbol["figi"],
                    # mic=symbol["mic"],
                    # type=symbol["type"],
                    **symbol
                )
        return symbols

    def get_symbol_quote(
            self,
            symbol: Symbol,
            price_type: str = None
    ) -> Decimal:
        """
        Returns current price for symbol. Price type is ignored, Finnhub only
        reports "last price".

        https://finnhub.io/docs/api/quote

        :param symbol: symbol to get quote for
        :type symbol: ztock.Symbol
        :param price_type: "bid", "mid" or "ask" price. Defaults to "ask"
            IGNORED BY FINNHUB
        :type price_type: str
        :return: current symbol price
        :rtype: decimal.Decimal
        """
        url = f"{self.api_url}/quote"
        params = {
            "symbol": symbol.name,
        }
        response = self.session.get(url, params=params)
        response.raise_for_status()
        price = parse_decimal(response.json()["c"])
        return price

    def get_candlesticks(
            self,
            symbol: Symbol,
            resolution: Union[str, int] = None,
            intervals: int = None
    ) -> List[Candlestick]:
        """
        Fetches symbol candlesticks.

        https://finnhub.io/docs/api/stock-candles

        :param symbol: symbol object
        :type symbol: ztock.broker.Symbol
        :param resolution: candlestick interval, defaults to 5 minutes
        :type resolution: int or str
        :param intervals: number of intervals to fetch, defaults to 50
        :type intervals: int
        :returns: list of candlestick objects
        :rtype: list of ztock.Candlestick
        """
        candlesticks = []

        # Define URL and parameters
        url = f"{self.api_url}/stock/candle"
        resolution = resolution or 5
        intervals = intervals or 50

        # Calculate from/to timestamps
        now = datetime.datetime.now()
        delta_time = None
        if (isinstance(resolution, int)):
            delta_time = datetime.timedelta(minutes=resolution * intervals)
        elif (resolution == "D"):
            delta_time = datetime.timedelta(days=intervals)
        elif (resolution == "W"):
            delta_time = datetime.timedelta(weeks=intervals)
        elif (resolution == "M"):
            delta_time = datetime.timedelta(days=intervals * 30)
        else:
            raise ValueError("Invalid candlestick resolution value: {}".format(resolution))

        from_datetime = now - delta_time
        from_timestamp = math.floor(from_datetime.timestamp())
        to_timestamp = math.ceil(now.timestamp())

        # Generate payload and send request
        params = {
            "symbol": symbol.name,
            "resolution": resolution,
            "from": from_timestamp - 1,
            "to": to_timestamp + 1,
        }
        self.logger.debug("Finnhub - Fetching candlesticks using request params {}".format(params))
        response = self.session.get(url, params=params)
        response.raise_for_status()

        # Unpack response, validate status and generate candlesticks
        data = response.json()
        status = data["s"]
        if (status == "no_data"):
            raise NoDataException(
                f"Finnhub - No candlestick data found for symbol {symbol.name} "
                f"using params: {params}"
            )
        elif (status != "ok"):
            raise Exception(
                "Finnhub - Unable to get candlestick data for symbol "
                f"{symbol.name} using params: {params}. API returned: {data}"
            )
        for i in range(len(data["c"])):
            open_ = data["o"][i]
            high = data["h"][i]
            low = data["l"][i]
            close = data["c"][i]
            volume = data["v"][i]
            candlesticks.append(Candlestick(open_, high, low, close, volume))
        latest_timestamp = datetime.datetime.fromtimestamp(data["t"][-1])
        self.logger.debug("{} - Latest candlestick timestamp: {}".format(
            self.name, latest_timestamp
        ))
        return candlesticks

    def get_average_price(
            self,
            symbol: Symbol,
            operation: str,
            days: int = None
    ) -> Dict[str, Union[int, Decimal]]:
        """
        Fetches candlesticks for given time period in days, and calculates
        average close price. Operation is not used since this function looks
        at candlesticks instead of actual orders.

        Returns a dict containing average close value and total volume as
        "average_price" and "volume" key-value pairs.

        :param symbol: symbol the get average price for
        :type symbol: ztock.broker.Symbol
        :param operation: not used
        :type operation: str
        :param days: number of days to fetch orders for. Defaults to 7
        :type days: int
        :return: order history with average price and volume
        :rtype: dict of (str, [int, Decimal])
        """
        # Get candlesticks
        days = days or 7
        candlesticks = self.get_candlesticks(symbol, "D", days)
        # Sum prices and volumes
        total_price = parse_decimal(0)
        volume = 0
        for candlestick in candlesticks:
            total_price += candlestick.close
            volume += candlestick.volume
        order_history = {
            "average_price": total_price / len(candlesticks),
            "volume": volume,
        }
        return order_history
