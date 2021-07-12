# -*- coding: utf-8 -*-
"""
Tests for broker modules.
"""
import os
import sys

sys.path.append(os.path.realpath(os.path.dirname(os.path.dirname(__file__))))
from ztock.config import Config
from ztock.logger import init_log
from ztock.brokers import init_broker
from ztock.symbol import Symbol


CONFIG = "test_config.json"


def main():
    """Authenticates and performs broker actions."""
    config = Config(CONFIG)

    # Init logger
    logger = init_log(config.logging)
    logger.info("Config: {}".format(config))

    for trader in config.traders:
        broker = init_broker(trader.broker)
        broker.refresh(log_ledger=True)

        # tsla = broker.lookup_symbol("TSLA")
        # broker.place_order(tsla, 1, "BUY", order_type="market")

        # symbol = broker.lookup_symbol("EURDKK")

        # positions = broker.get_positions()
        # print(f"\nPositions:\n{positions}\n")

        # order = broker.place_order(symbol, 10000, "BUY", order_type="limit", price=7)
        # print(f"\nPlaced order:\n{order}\n")

        open_orders = broker.get_live_orders()
        print(f"\nOpen orders:\n{open_orders}\n")

        # cancelled_order = broker.cancel_order(order)
        # print(f"\nCancelled order:\n{cancelled_order}\n")

        cancelled_orders = broker.cancel_stale_orders()
        print(f"\nCancelled stale orders:\n{cancelled_orders}\n")

        # order = broker.place_order(symbol, 1000, "BUY", order_type="market")
        # print(f"\nPlaced order:\n{order}\n")

        positions = broker.get_positions()
        print(f"\nPositions:\n{positions}\n")

        if (len(positions) > 0):
            order = broker.place_order(positions[0].symbol, 1000, "SELL")
            print(f"\Sell order:\n{order}\n")
    return
 

if (__name__ == "__main__"):
    main()
