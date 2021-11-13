# -*- coding: utf-8 -*-
import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from . import patterns
from .config import Config
from .constants import LOG_NAME
from .exceptions import NoDataException
from .markets import Market
from .patterns.candlestick import CandlestickPattern
from .symbol import Symbol


class Analyzer:
    """
    Trend analysis class.
    """
    def __init__(self, config: Config, market: Market) -> None:
        """
        Wrapper for market APIs. Reads market data vendor info from config.

        :param config: path to market configuration file
        :type config: ztock.config.Config
        :param market: market data instance
        :type market: ztock.market.Market
        """
        self.id = uuid.uuid4()
        self.market = market
        # Read config
        self.config = config

        # Get logger(s)
        self.logger = logging.getLogger(LOG_NAME)
        return

    def run(self) -> None:
        """Performs configured trend analysis run."""
        self.logger.info("{} {} - Starting analysis ----------------------------------".format(
            self.market.name, self.id
        ))
        # Loop through symbols in configured exchanges and run trend analysis
        results = {}
        exchanges = vars(self.config.exchanges)
        for exchange, mic_codes in exchanges.items():
            symbols = self.analyze_exchange(exchange, mic_codes)
            results[exchange] = symbols

        # Dump results to file
        with open(self.config.output_path, "w") as output:
            json.dump(results, output)
        return

    def analyze_exchange(
            self, exchange: str, mic_codes: Optional[Union[List[str], str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Performs analysis of all symbols in exchange.

        Returns a dict with symbols and custom dict of trend analysis results
        as key-values.

        :param exchange: exchange code
        :type exchange: str
        :param mic_codes: optional list of MIC codes
        :type mic_codes: list of str or str
        :return: trend analysis results dict
        :rtype: dict of (str, dict)
        """
        self.logger.debug("{} {} - Listing symbols for exchange {}".format(
            self.market.name, self.id, exchange
        ))
        # Get exchange symbols
        symbols = self.market.list_symbols(
            exchange, symbol_type="Common Stock", mic_codes=mic_codes
        )
        self.logger.debug("{} {} - Symbols: {}".format(self.market.name, self.id, symbols))
        # Analyze symbols and return results
        results = {}
        for symbol in symbols.values():
            self.logger.debug("{} {} - Analyzing {} symbol {}".format(
                self.market.name, self.id, exchange, symbol.name
            ))
            patterns = self.analyze_symbol(symbol)
            if (patterns is None):
                continue

            score = sum([pattern.indication for pattern in patterns])
            # Print recognized strong positive patterns
            if (score > 100.0 or any(pattern.indication > 100.0 for pattern in patterns)):
                self.log_new_patterns(symbol, exchange, score, patterns)

            # Convert timestamp to string if defined
            timestamp = None
            if (patterns[-1].timestamp is not None):
                timestamp = patterns[-1].timestamp.strftime("%Y.%m.%d %H:%M:%S")

            results[exchange] = {
                "patterns": {
                    pattern.name: pattern.indication
                    for pattern in patterns
                    if pattern.indication != 0
                },
                "score": score,
                "timestamp": timestamp,
                "name": f" ({symbol.description})" if (symbol.description) else "",
                "market": symbol.mic,
            }
        return results

    def analyze_symbol(self, symbol: Symbol) -> List[CandlestickPattern]:
        # Get candlesticks
        try:
            candles = self.market.get_candlesticks(symbol, self.config.candlestick_resolution)
        except NoDataException:
            self.logger.debug("{} - {}: No candlesticks returned".format(
                self.market.name, symbol.name
            ))
            return None
        except Exception:
            self.logger.exception("{} - Unable to get candlesticks for symbol {}".format(
                self.market.name, symbol
            ))
            return None

        # Validate candlesticks
        if (len(candles) < 5):
            self.logger.debug("{} - {}: Less than 5 candlesticks found, skipping analysis".format(
                self.market.name, symbol.name
            ))
            return None
        if (
                candles[-1].timestamp is not None
                and not self.validate_candle_age(candles[-1].timestamp)
        ):
            return None

        # Analyze candlesticks for trends
        results = patterns.analyze_candlesticks(candles)
        return results

    def validate_candle_age(self, timestamp: datetime.datetime):
        """Validates candlestick age. Returns True if valid or False if too old for analysis."""
        now = datetime.datetime.now()
        resolution = self.config.candlestick_resolution

        if (resolution >= 1440):
            # Daily or larger resolution candlesticks
            candlestick_age = (now.date() - timestamp.date()).days
            # Allowing Friday's data on Monday
            valid_age = 1 if (now.weekday() > 0) else 3
        else:
            # Other candlestick resolutions
            candlestick_age = (now - timestamp).total_seconds()
            valid_age = resolution * 2

        if (candlestick_age > valid_age):
            self.logger.debug(
                "{} - Latest candlestick too old ({} > {}), skipping symbol".format(
                    self.market.name, candlestick_age, valid_age
                )
            )
            return False
        return True

    def log_new_patterns(
            self,
            symbol: str,
            exchange_code: str,
            score: float,
            results: List[CandlestickPattern]
    ) -> None:
        """Logs newly recognized patterns along with total symbol indication score."""
        recognized_patterns = [pattern for pattern in results if pattern.indication != 0.0]
        pattern_strings = self.generate_pattern_strings(recognized_patterns)
        symbol_desc = f" ({symbol.description})" if (symbol.description) else ""
        self.logger.info(
            "Score: {} -- {} {}{} -- Pattern(s): {}".format(
                int(score),
                symbol.mic or exchange_code, symbol.name, symbol_desc,
                ", ".join(pattern_strings)
            )
        )
        return

    def generate_pattern_strings(self, patterns: List[CandlestickPattern]) -> List[str]:
        """Returns list of pattern display strings."""
        pattern_strings = [
            f"{pattern.name} [{pattern.indication}]"
            for pattern in patterns
        ]
        return pattern_strings
