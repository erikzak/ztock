# -*- coding: utf-8 -*-
"""
Functions for analyzing candlestick patterns using TA-lib.
"""
from typing import Callable, Dict, List

import numpy as np
import talib.abstract
from numpy import ndarray

from .pattern import Pattern
from ..candlestick import Candlestick


class CandlestickPattern(Pattern):
    """Base candlestick pattern class."""
    timestamp = None

    def __init__(
            self,
            name: str,
            talib_func: Callable[[Dict[str, ndarray]], float],
            validators: List[Callable[..., bool]] = None,
            weight: int = None
    ) -> None:
        """
        Inits candlestick pattern object.

        :param name: name of pattern
        :type name: str
        :param talib_func: TA-Lib package function
        :type talib_func: def
        :param validators: functions for validating recognized pattern
        :type validators: list of def
        :param weight: weight of candlestick pattern
        :type weight: float
        """
        self.name = name
        self.function = talib_func
        self.validators = validators
        self.weight = weight or 1.0
        return

    def get_indication(self, candlesticks: Candlestick) -> float:
        """
        Analyzes candlesticks for defined pattern.

        :param candlesticks: candlesticks to analyze for pattern
        :type candlesticks: list of Candlestick
        :return: pattern indication value
        :rtype: float
        """
        # Extract candlestick values to convert to numpy arrays
        open_, high, low, close, volume = [], [], [], [], []
        for candle in candlesticks:
            open_.append(candle.open)
            high.append(candle.high)
            low.append(candle.low)
            close.append(candle.close)
            volume.append(candle.volume)
        # Convert to numpy arrays
        inputs = {
            'open': np.asarray(open_, dtype=np.float64),
            'high': np.asarray(high, dtype=np.float64),
            'low': np.asarray(low, dtype=np.float64),
            'close': np.asarray(close, dtype=np.float64),
            'volume': np.asarray(volume, dtype=np.float64)
        }

        # Optionally add timestamp
        if (candlesticks[-1].timestamp is not None):
            self.timestamp = candlesticks[-1].timestamp

        # Run pattern detection and validate results
        analysis = self.function(inputs)
        indication = analysis[-1]
        if (not self.validate(indication, inputs)):
            indication = 0.0
        self.indication = indication * self.weight
        return self.indication

    def validate(self, indication: float, inputs: Dict[str, ndarray]) -> bool:
        """
        Validates a positive/negative pattern indication, e.g. if it relies on
        a previous candlestick trend.

        :param indication: pattern indication value
        :type indication: float
        :param inputs: input candlestick values
        :type inputs: dict of (str, numpy.ndarray)
        :return: validation result
        :rtype: bool
        """
        if (indication != 0.0 or self.validators is None):
            return True
        if (any(
            validator(indication, inputs) is False
            for validator in self.validators
        )):
            return False
        return True


# Candlestick validation functions
def reversal_if_trend(
        indication: float,
        inputs: Dict[str, ndarray],
        factor: int = 1,
        skip: int = 0
) -> bool:
    """
    Checks if candlesticks have a trend leading up to pattern. A positive
    indicator relies on downwards trend, and vice versa.

    :param indication: pattern indication value
    :type indication: float
    :param inputs: input candlestick values
    :type inputs: dict of (str, numpy.ndarray)
    :param factor: number of close values to use for trend validation
    :type factor: int
    :param skip: number of close values to skip when validating trend
    :type skip: int
    :return: validation result
    :rtype: bool
    """
    # Get latest close average
    latest_close = inputs["close"][-1 * factor - skip:]
    avg_latest_close = sum(latest_close) / len(latest_close)
    # Get average close of candlesticks prior to latest set
    previous_close = inputs["close"][-5 * factor - skip:-1 * factor - skip]
    avg_previous_close = sum(previous_close) / len(previous_close)
    # See if trend fits
    if (indication > 0.0 and avg_latest_close < avg_previous_close):
        return True
    elif (indication < 0.0 and avg_latest_close > avg_previous_close):
        return True
    return False


def reversal_if_long_trend(indication: float, inputs):
    """Checks if candlesticks have a long trend leading up to pattern."""
    return reversal_if_trend(indication, inputs, factor=2)


def reversal_if_previous_trend_skip1(indication, inputs):
    """Checks if candlesticks have a trend leading up to pattern, skipping
    latest close value."""
    return reversal_if_trend(indication, inputs, skip=1)


def reversal_if_previous_trend_skip3(indication, inputs):
    """Checks if candlesticks have a trend leading up to pattern, skipping
    three latest close values."""
    return reversal_if_trend(indication, inputs, skip=3)


def analyze_candlesticks(candles: List[Candlestick]) -> List[CandlestickPattern]:
    """
    Uses TA-Lib to analyze candlesticks, and returns
    a result dict containing the following keys:

    :param candles: list of Candlestick objects
    :type candles: list of ztock.Candlestick
    :return: list of checked patterns
    :rtype: list of ztock.patterns.CandlestickPattern
    """
    results = get_candlestick_patterns()
    for pattern in results:
        pattern.get_indication(candles)
    return results


def get_candlestick_patterns():
    """
    Returns list of CandlestickPattern recognition functions
    """
    # pylint: disable=no-member
    patterns = [
        CandlestickPattern(
            "Abandoned baby",
            talib.abstract.CDLABANDONEDBABY,
            [reversal_if_trend],
            weight=2.0
        ),
        CandlestickPattern(
            "Breakaway",
            talib.abstract.CDLBREAKAWAY,
            [reversal_if_trend],
            weight=2.0
        ),
        CandlestickPattern(
            "Dark cloud cover",
            talib.abstract.CDLDARKCLOUDCOVER,
            [reversal_if_previous_trend_skip1]
        ),
        CandlestickPattern(
            "Dragonfly doji",
            talib.abstract.CDLDRAGONFLYDOJI,
            [reversal_if_long_trend]
        ),
        CandlestickPattern(
            "Engulfing pattern",
            talib.abstract.CDLENGULFING,
            [reversal_if_previous_trend_skip1]
        ),
        CandlestickPattern(
            "Evening doji star",
            talib.abstract.CDLEVENINGDOJISTAR,
            [reversal_if_long_trend]
        ),
        CandlestickPattern(
            "Evening star",
            talib.abstract.CDLEVENINGSTAR,
            [reversal_if_trend],
            weight=2.0
        ),
        CandlestickPattern(
            "Hammer",
            talib.abstract.CDLHAMMER,
            [reversal_if_long_trend]
        ),
        CandlestickPattern(
            "Hanging man",
            talib.abstract.CDLHANGINGMAN,
            [reversal_if_long_trend]
        ),
        CandlestickPattern(
            "Morning doji star",
            talib.abstract.CDLMORNINGDOJISTAR,
            [reversal_if_long_trend]
        ),
        CandlestickPattern(
            "Morning star",
            talib.abstract.CDLMORNINGSTAR,
            [reversal_if_trend]
        ),
        CandlestickPattern(
            "Shooting star",
            talib.abstract.CDLSHOOTINGSTAR,
            [reversal_if_trend]
        ),
        CandlestickPattern(
            "Three advancing white soldiers",
            talib.abstract.CDL3WHITESOLDIERS,
            [reversal_if_previous_trend_skip3]
        ),
        CandlestickPattern(
            "Three black crows",
            talib.abstract.CDL3BLACKCROWS,
            [reversal_if_previous_trend_skip3],
            weight=2.0
        ),
        CandlestickPattern(
            "Three inside up/down",
            talib.abstract.CDL3INSIDE,
            [reversal_if_previous_trend_skip3]
        ),
        CandlestickPattern(
            "Three line strike",
            talib.abstract.CDL3LINESTRIKE,
            [reversal_if_previous_trend_skip3],
            weight=2.0
        ),
        CandlestickPattern(
            "Three outside up/down",
            talib.abstract.CDL3OUTSIDE,
            [reversal_if_previous_trend_skip3]
        ),
        CandlestickPattern(
            "Two crows",
            talib.abstract.CDL2CROWS,
            [reversal_if_previous_trend_skip1]
        ),
        CandlestickPattern(
            "Upside gap with two crows",
            talib.abstract.CDLUPSIDEGAP2CROWS,
            [reversal_if_previous_trend_skip1]
        ),
        CandlestickPattern(
            "Upside/Downside Gap Three Methods",
            talib.abstract.CDLXSIDEGAP3METHODS,
            [reversal_if_previous_trend_skip1]
        ),
    ]
    return patterns
