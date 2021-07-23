# -*- coding: utf-8 -*-
"""
ztock package for automated technical analysis and trading of stocks.
"""
import datetime
import logging
import pickle
import time

from .config import Config
from .constants import LOG_NAME
from .logger import init_log, flush_log, set_log_level
from .markets import init_market
from .trader import Trader


def run(config_file: str) -> None:
    """
    Continuous trading mode. Keeps running trade and sleeping for set
    duration between runs.

    :param config_file: path to config file
    :type config_file: str
    """
    config = Config(config_file)

    # Init logger
    if (hasattr(config, "logging")):
        logger = init_log(config.logging)
    else:
        logger = logging.getLogger(LOG_NAME)
    logger.info("Config: {}".format(config))

    # Set up traders
    traders = _init_traders(config)
    cached_traders = pickle.dumps(config.traders)

    # Run traders at set intervals
    while (True):
        # Re-read config and apply log level
        config.refresh()
        set_log_level(getattr(config.logging, "level", None))

        # Check if list of configured traders has changed. If yes, reinitialize traders
        if (pickle.dumps(config.traders) != cached_traders):
            logger.info("Trader configs updated, reinitializing trader instances")
            traders = _init_traders(config)
            for trader in traders:
                trader.next_run = trader.calculate_next_run()
            cached_traders = pickle.dumps(config.traders)

        # Loop through traders and see if they should be run
        for trader in traders:
            if (trader.next_run is None or datetime.datetime.now() < trader.next_run):
                continue

            # Trading run
            try:
                trader.trade()
                logger.info("{} - Next run: {}".format(trader.broker.name, trader.next_run))
                # Flush log handlers to send any error mails
                flush_log()
            except Exception:
                logger.exception("{} - Unable to perform trading run".format(trader.id))
                trader.calculate_next_run()
        time.sleep(1)
    return


def _init_traders(config: Config):
    """Inits trader objects based on configs."""
    # Set up market data vendor object
    market = init_market(config.market_data)

    traders = []
    for trader_config in config.traders:
        traders.append(Trader(trader_config, market))
    return traders


__all__ = [
    "LOG_NAME",
    "run",
]
