# -*- coding: utf-8 -*-
import datetime
import logging
import math
import uuid
from decimal import Decimal
from typing import List, Optional

from requests import HTTPError

from . import patterns, utils
from .brokers import Position, init_broker
from .config import Config
from .constants import LOG_NAME, ORDER_LOG_NAME
from .currency import convert_currency
from .exceptions import NoDataException, UnknownExchange
from .exchange import Exchange
from .markets import Market
from .patterns.candlestick import CandlestickPattern
from .symbol import Symbol


class Trader:
    """
    Main trader module, used to read config, init broker and market data objects
    and perform trading runs.
    """
    def __init__(self, config: Config, market: Market) -> None:
        """
        Trading wrapper for broker APIs. Reads vendor and authentication info
        from config.

        :param config: trader configuration
        :type config: ztock.config.Config
        """
        self.id = uuid.uuid4()
        self.market = market
        # Read config
        self.config = config

        # Get logger(s)
        self.logger = logging.getLogger(LOG_NAME)
        self.order_logger = logging.getLogger(ORDER_LOG_NAME)

        # Init broker object
        try:
            self.broker = init_broker(self.config.broker)
        except Exception:
            self.logger.exception("Unable to init trader")
            raise

        # Set next run to now
        self.next_run = datetime.datetime.now()
        return

    def price_is_right(
            self,
            symbol: str,
            operation: str,
            price: Decimal,
            min_orders: int = None,
            days: Optional[int] = None
    ) -> bool:
        """
        Checks if the price of a buy or sell order is favorable by comparing
        it to the average of recent orders.

        :param symbol: symbol to check
        :type symbol: str
        :param operation: order operation, 'BUY' or 'SELL'
        :type operation: str
        :param price: price per quantity to compare against recent orders
        :type price: Decimal
        :param min_orders: minimum amount of orders for validating price
            against average. Defaults to 5
        :type min_orders: int
        :param days: optional number of days to fetch orders for. Defaults to 7
        :type days: int
        :return: flag indicating if buy price is right
        :rtype: bool
        """
        min_orders = min_orders if (min_orders is not None) else 5
        days = days or 7
        order_history = self.market.get_average_price(symbol, operation, days)
        if (
                order_history["volume"] >= min_orders
                and (
                    (operation == "BUY" and price > order_history["average_price"])
                    or (operation == "SELL" and price < order_history["average_price"])
                )
        ):
            return False
        return True

    def place_market_buy_order(self, symbol: Symbol, exchange: Optional[Exchange] = None) -> None:
        """
        Places a market buy order using broker API.

        :param symbol: symbol to buy
        :type symbol: ztock.Symbol
        :param exchange: optional exchange object
        :type exchange: ztock.Exchange
        """
        self.logger.debug("{} - Preparing market buy order for {}".format(
            self.broker.name, symbol
        ))
        # Get symbol quote
        price = self.market.get_symbol_quote(symbol)
        if (symbol.currency != self.broker.currency):
            account_currency_price = convert_currency(
                price,
                symbol.currency,
                self.broker.currency
            )
        else:
            account_currency_price = price

        # Calculate quantity
        buy_amount = self.broker.cash_balance * self.config.buy_fraction
        quantity = math.floor(buy_amount / account_currency_price)
        order_amount = quantity * account_currency_price
        self.logger.debug(
            "{0} - Buy fraction: {1:.2f} {2} ({3:.2f} {2} * {4}). "
            "Order amount: {5:.2f} {2} ({6} * {7:.2f} {2})".format(
                self.broker.name, buy_amount, self.broker.currency, self.broker.cash_balance,
                self.config.buy_fraction, order_amount, quantity, account_currency_price
            )
        )
        # Adjust to minimum configured buy value
        min_buy_amount = getattr(self.config, "min_buy_amount", 0)
        if (order_amount < min_buy_amount):
            while (account_currency_price and order_amount < min_buy_amount):
                quantity += 1
                order_amount = quantity * account_currency_price
            self.logger.debug(
                "{0} - Adjusting order amount to minimum buy: {1:.2f} {2} "
                "({3} * {4:.2f} {2})".format(
                    self.broker.name, order_amount, self.broker.currency,
                    quantity, account_currency_price
                )
            )
        # Adjust to maximum configured buy value
        max_buy_amount = getattr(self.config, "max_buy_amount", None)
        if (max_buy_amount and order_amount > max_buy_amount):
            if (quantity == 1):
                self.logger.warning(
                    "{} - {}: No buy order, stock price exceeds configured "
                    "maximum buy amount ({:.2f} > {:.2f})".format(
                        self.broker.name, symbol.name, order_amount, max_buy_amount
                    )
                )
                return
            while (account_currency_price and quantity > 1 and order_amount > max_buy_amount):
                quantity -= 1
                order_amount = quantity * account_currency_price
            self.logger.debug(
                "{0} - Adjusting order amount to maximum buy: {1:.2f} {2} "
                "({3} * {4:.2f} {2})".format(
                    self.broker.name, order_amount, self.broker.currency,
                    quantity, account_currency_price
                )
            )

        # Check if we have funds
        min_broker_balance = getattr(self.config, "min_broker_cash_balance", 0)
        if (order_amount > self.broker.cash_balance + min_broker_balance):
            self.logger.info(
                "{0} - {1}: No buy order, funds too low ({2:.2f} {3} > {4:.2f} {3} + {5:.2f} {3})"
                " to place order".format(
                    self.broker.name, symbol.name, order_amount, self.broker.currency,
                    self.broker.cash_balance, min_broker_balance
                )
            )
            return

        # Place buy order
        try:
            self.logger.info(
                "{0} - Placing {1} market buy order: {2:.2f} {3} @ {4:.2f} {5} "
                "(total: {6:.2f} {5})".format(
                    self.broker.name, exchange or "", quantity, symbol.name, price,
                    symbol.currency, quantity * price
                ).replace("  ", " ")
            )
            order = self.broker.place_buy_order(symbol, quantity=quantity, exchange=exchange)
            self.logger.info("{} - {}: Buy order {} placed".format(
                self.broker.name, symbol.name, order.id
            ))
        except Exception:
            self.logger.exception("Unable to place market buy order")
        return

    def place_market_sell_order(self, position: Position) -> None:
        """
        Places a market sell order for an open trade.

        :param position: position to close
        :type order: ztock.broker.Position
        """
        self.logger.debug("Preparing market sell order for {}".format(position.symbol))
        # Get symbol quote
        price = self.market.get_symbol_quote(position.symbol)
        exchange = getattr(position.symbol, "exchange", None)

        try:
            self.logger.info(
                "Placing {0} market sell order: {1:.2f} {2} @ {3:.2f} {4} "
                "(total: {5:.2f} {4})".format(
                    exchange or "", position.quantity, position.symbol.name, price,
                    self.broker.currency, position.quantity * price
                ).replace("  ", " ")
            )
            order = self.broker.place_sell_order(position)
            order_log_msg = "{}: Sell order {} placed".format(position.symbol.name, order.id)
            self._log_order(order_log_msg)
        except Exception:
            self.logger.exception("Unable to place market sell order")
        return

    def log_new_patterns(
            self,
            symbol_name: str,
            avg_indication: float,
            results: List[CandlestickPattern]
    ) -> None:
        """Logs newly recognized patterns along with average indication."""
        recognized_patterns = [pattern for pattern in results if pattern.indication != 0.0]
        pattern_strings = [
            "{} [{}]".format(pattern.name, pattern.indication)
            for pattern in recognized_patterns
        ]
        self.logger.info(
            "{}: Average indication value: {}. Pattern(s): {}".format(
                symbol_name, round(avg_indication, 2), ", ".join(pattern_strings)
            )
        )
        return

    def get_symbols(self, pick_random: bool = True) -> List[Symbol]:
        """Generates list of symbols to analyze for patterns based on user configuration."""
        symbols = []
        exchanges = vars(self.config.exchanges)
        for exchange_code, user_symbols in exchanges.items():
            # Check if exchange is open
            try:
                exchange = Exchange(exchange_code)
                if (not exchange.is_open()):
                    self.logger.info(
                        "Exchange {} is closed, skipping related symbols".format(exchange_code)
                    )
                    continue
            except UnknownExchange:
                self.logger.error("Unknown exchange code: {}".format(exchange_code))

            # Get exchange symbols and look for any configured symbols to add
            try:
                exchange_symbols = self.market.list_symbols(exchange_code, "Common Stock")
            except NotImplementedError:
                # Market data vendor does not supply symbol list. Generate
                # Symbol classes per user symbol instead
                exchange_symbols = None

            for user_symbol in user_symbols:
                # Check for random symbol flag. Only works when list of all
                # exchange symbols is available
                if (user_symbol.upper().startswith("_RANDOM_")):
                    if (not pick_random):
                        continue
                    if (exchange_symbols):
                        # Pick n random symbols
                        n_rand = int(user_symbol.split("_")[-1])
                        random_symbols = utils.pick_random_symbols(
                            n_rand, exchange_symbols, user_symbols
                        )
                        self.logger.info("Adding {} random symbols from exchange {}: {}".format(
                            n_rand, exchange_code, [symbol.name for symbol in random_symbols]
                        ))
                        symbols.extend(random_symbols)
                    else:
                        self.logger.warning(
                            "Market data vendor does not support exchange symbol list, "
                            "unable to add random symbols from {}".format(exchange_code)
                        )

                else:
                    if (exchange_symbols is not None):
                        # Exchange symbols generated, see if user symbol is in list
                        if (user_symbol not in exchange_symbols):
                            self.logger.error(
                                "Symbol {} not found in exchange {}, skipping "
                                "symbol".format(user_symbol, exchange_code)
                            )
                            continue
                        symbols.append(exchange_symbols[user_symbol])

                    else:
                        # Lookup individual symbols
                        symbol = self.market.lookup_symbol(user_symbol)
                        symbols.append(symbol)
        return symbols

    def get_symbol_names(self) -> List[str]:
        """Returns a list of configured symbol names to trade across exchanges."""
        symbol_names = []
        exchanges = vars(self.config.exchanges)
        for user_symbols in exchanges.values():
            symbol_names.extend(user_symbols)
        return symbol_names

    def check_positions_for_sell_candidates(self):
        """
        Fetches open trades, analyses candlesticks for negative trend patterns
        and tries to sell high.
        """
        self.logger.info("Inspecting open positions for sell candidates")

        # Get positions
        positions = self.broker.get_positions()
        self.logger.debug("{} - Current open positions: {}".format(self.broker.name, positions))

        # Remove positions in closed in exchanges
        self.remove_closed_exchange_positions(positions)
        # Remove non-configured symbols
        self.remove_non_configured_positions(positions)

        for position in positions:
            # Perform profitability check, if enabled
            if (
                    hasattr(self.config, "profit_check")
                    and getattr(self.config.profit_check, "enabled", False)
            ):
                min_profit_fraction = getattr(self.config.profit_check, "min_profit_fraction", 0)
                min_profit = position.market_value * min_profit_fraction
                min_profit += self.broker.minimum_order_fee * 2
                if (position.pnl and position.pnl < min_profit):
                    self.logger.info(
                        "{0}: Skipping analysis due to profitability check: "
                        "{1:.2f} {2} < {3:.2f} {2} target ({4:.2f} {2} * {5} + "
                        "{6} {2} * 2)".format(
                            position.symbol.name, position.pnl, position.currency,
                            min_profit, position.market_value, min_profit_fraction,
                            self.broker.minimum_order_fee
                        )
                    )
                    continue

            # Get candlesticks
            try:
                candlesticks = self.market.get_candlesticks(
                    position.symbol,
                    self.config.candlestick_resolution
                )
            except NoDataException:
                self.logger.warning("{} - {}: No candlesticks returned".format(
                    self.market.name, position.symbol.name
                ))
                continue
            except Exception:
                self.logger.exception("{} - Unable to get candlesticks for symbol {}".format(
                    self.market.name, position.symbol
                ))
                continue

            if (len(candlesticks) < 5):
                self.logger.info("{}: Less than 5 candlesticks found, skipping analysis".format(
                    position.symbol.name
                ))
                continue

            # Analyze candlesticks for trends
            results = patterns.analyze_candlesticks(candlesticks)
            avg_indication = sum([pattern.indication for pattern in results]) / len(results)

            # Determine if position should be closed, continue if no patterns detected
            if (avg_indication == 0):
                self.logger.info("{}: No candlestick patterns detected".format(position.symbol.name))
                continue

            # Print recognized patterns along with average indicator
            self.log_new_patterns(position.symbol.name, avg_indication, results)

            # Sell if trend indication value is positive
            if (avg_indication < 0):
                self.place_market_sell_order(position)
        return positions

    def remove_closed_exchange_positions(self, positions: List[Position]) -> None:
        """Removes positions from given list if position exchange is closed for trading."""
        logged_exchanges = set()
        for exchange_code, exchange_symbols in vars(self.config.exchanges).items():
            try:
                exchange = Exchange(exchange_code)
            except UnknownExchange:
                self.logger.error("Unknown exchange code: {}".format(exchange_code))
                continue
            for i, position in reversed(list(enumerate(positions))):
                if (position.symbol.name in exchange_symbols and not exchange.is_open()):
                    positions.pop(i)
                    if (exchange_code not in logged_exchanges):
                        self.logger.info("Exchange {} is closed, skipping related symbols".format(
                            exchange_code
                        ))
                        logged_exchanges.add(exchange_code)
        return

    def remove_non_configured_positions(self, positions: List[Position]) -> None:
        """Removes positions from given list if symbol not configured for trading."""
        trader_symbols = self.get_symbol_names()
        for i, position in reversed(list(enumerate(positions))):
            if (position.symbol.name not in trader_symbols):
                positions.pop(i)
        return

    def check_market_for_potential_buy_candidates(self) -> None:
        """
        Gets lists of defined/random symbols for configured exchanges,
        analyses candlesticks for positive trend patterns and tries to buy
        low.
        """
        self.logger.info("Analyzing market for buy candidates")

        # Get configured symbols to check symbols for patterns, along with open positions
        symbols = self.get_symbols()
        positions = self.broker.get_positions()
        position_sums = {}
        for position in positions:
            position_sum = position_sums.get(position.symbol.name, None)
            if (position_sum is None):
                position_sums[position.symbol.name] = position
            else:
                position_sum.market_value += position.market_value

        for symbol in symbols:
            self.logger.debug("Analyzing {}".format(symbol))

            # If existing open positions exceed configured max, skip symbol
            buy_amount = self.broker.cash_balance * self.config.buy_fraction
            min_buy_amount = getattr(self.config, "min_buy_amount", 0)
            max_position_multiplier = getattr(self.config, "max_position_value", 0)
            max_position_value = max(buy_amount, min_buy_amount) * max_position_multiplier
            if (symbol.name in position_sums and max_position_value > 0):
                position = position_sums[symbol.name]
                if (position.exchange_rate):
                    market_value = position.market_value * position.exchange_rate
                else:
                    market_value = convert_currency(
                        position.market_value,
                        position.currency,
                        self.broker.currency
                    )
                if (market_value and market_value > max_position_value):
                    self.logger.info(
                        "{0}: Skipping symbol, open position's market value "
                        "exceeds configured max amount ({1:.2f} {2} > {3:.2f} {2})".format(
                            position.symbol.name, market_value,
                            self.broker.currency, max_position_value
                        )
                    )
                    continue

            # Get candlesticks
            try:
                candlesticks = self.market.get_candlesticks(
                    symbol,
                    self.config.candlestick_resolution
                )
            except NoDataException:
                self.logger.warning("{}: No candlesticks returned".format(symbol.name))
                continue
            except Exception:
                self.logger.exception("Unable to get candlesticks for symbol {}".format(symbol))
                continue

            if (len(candlesticks) < 5):
                self.logger.info(
                    "{}: Less than 5 candlesticks found, skipping analysis".format(symbol.name)
                )
                continue

            # Analyze candlesticks for trends
            results = patterns.analyze_candlesticks(candlesticks)
            avg_indication = sum([pattern.indication for pattern in results]) / len(results)

            # Determine if potential buy, continue if no patterns detected
            if (avg_indication == 0):
                self.logger.info("{}: no patterns".format(symbol.name))
                continue

            # Print recognized patterns
            self.log_new_patterns(symbol.name, avg_indication, results)

            # Buy if trend indication value is positive
            if (avg_indication > 0):
                self.place_market_buy_order(symbol)
                # Refresh broker ledger
                self.broker.refresh()
        return

    def calculate_next_run(self) -> datetime.datetime:
        """
        Calculates when to run the trader again based on configured wait period.

        :return: datetime for next run
        :rtype: datetime.datetime
        """
        wait = datetime.timedelta(seconds=self.config.sleep_duration)
        next_run = datetime.datetime.now() + wait
        # Round next run to sleep duration interval + market vendor delay
        # (to allow candlestick intervals to update)
        next_run -= datetime.timedelta(
            minutes=next_run.minute % (self.config.sleep_duration / 60),
            seconds=next_run.second,
            microseconds=next_run.microsecond
        )
        interval_delay = getattr(self.market.config, "interval_delay", 0)
        next_run += datetime.timedelta(interval_delay)
        return next_run

    def _log_order(self, msg: str) -> None:
        """
        Logs order, checking if dedicated order notification mail handler
        is set up.

        :param msg: message to log
        :type msg: str
        """
        self.logger.info(msg)
        self.order_logger.info(msg)
        return

    def trade(self) -> None:
        """
        Performs a trading run.
        """
        self.next_run = None
        self.logger.info("{} {} - Starting trading run ----------------------------------".format(
            self.broker.name, self.id
        ))

        # Refresh market vendor connection
        self.market.refresh()
        try:
            # Refresh broker connection and info
            self.broker.refresh(log_ledger=True)
        except HTTPError as error:
            if (error.response.status_code == 401):
                self.logger.error("Unauthorized to refresh broker, check authentication/gateway")
                self.next_run = self.calculate_next_run()
                return
            raise

        # Get/validate live orders
        live_orders = self.broker.get_live_orders()
        self.logger.debug("Live orders: {}".format(live_orders))
        self.broker.cancel_stale_orders(live_orders, self.config.order_lifetime)

        # Check positions for negative trends to potentially close trades
        if (getattr(self.config, "sell", True)):
            self.check_positions_for_sell_candidates()

        # Check defined/random exchange symbols for positive trends to potentially buy
        if (getattr(self.config, "buy", True)):
            min_buy_amount = getattr(self.config, "min_buy_amount", 0)
            min_broker_balance = getattr(self.config, "min_broker_cash_balance", 0)
            if (self.broker.cash_balance > min_buy_amount + min_broker_balance):
                # Refresh broker ledger
                self.broker.refresh()
                self.check_market_for_potential_buy_candidates()
            else:
                self.logger.info(
                    "Available broker cash balance less than configured minimum "
                    "buy order amount, skipping analysis of potential buy "
                    "candidates ({0:.2f} {1} < {2:.2f} {1} + {3:.2f}) {1}".format(
                        self.broker.cash_balance, self.broker.currency,
                        min_buy_amount, min_broker_balance
                    )
                )

        # Calculate next run time
        self.next_run = self.calculate_next_run()
        return
