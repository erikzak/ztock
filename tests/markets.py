# -*- coding: utf-8 -*-
"""
Tests for market data vendor modules.
"""
import os
import sys

sys.path.append(os.path.realpath(os.path.dirname(os.path.dirname(__file__))))
from ztock.config import Config
from ztock.logger import init_log
from ztock.markets import init_market


CONFIG = "test_config.json"


def main():
    """Authenticates and fetches example market data."""
    config = Config(CONFIG)

    # Init logger
    logger = init_log(config.logging)
    logger.info("Config: {}".format(config))

    market = init_market(config.market_data)

    # symbols = market.list_symbols("NASDAQ")
    # print(symbols)

    symbol = market.lookup_symbol("SEKDKK")
    # print(symbol)

    # quote = market.get_symbol_quote(symbol)
    # print(quote)

    candlesticks = market.get_candlesticks(symbol, resolution=15)
    print(candlesticks)

    # avg_price = market.get_average_price(symbol, "BUY", 10)
    # print(avg_price)
    return


if (__name__ == "__main__"):
    main()
