# -*- coding: utf-8 -*-
"""
Handles candlestick objects with functionality for TA-Lib pattern recognition.
"""
import datetime
from decimal import Decimal
from typing import Optional, Union

from .utils import parse_decimal


class Candlestick:
    """Candlestick class."""
    def __init__(
            self,
            open_: Union[float, Decimal],
            high: Union[float, Decimal],
            low: Union[float, Decimal],
            close: Union[float, Decimal],
            volume: Optional[Union[float, Decimal, None]] = None,
            timestamp: Optional[datetime.datetime] = None
    ):

        """
        Inits candlestick object with data.

        :param open_: candlestick open value
        :type open_: float or decimal.Decimal
        :param high: candlestick high value
        :type high: float or decimal.Decimal
        :param low: candlestick low value
        :type low: float or decimal.Decimal
        :param close: candlestick close value
        :type close: float or decimal.Decimal
        :param volume: optional candlestick volume value
        :type volume: float or decimal.Decimal
        :param timestamp: optional candlestick close timestamp
        :type timestamp: datetime.datetime
        """
        self.open = parse_decimal(open_)
        self.high = parse_decimal(high)
        self.low = parse_decimal(low)
        self.close = parse_decimal(close)
        self.volume = parse_decimal(volume) if (volume is not None) else None
        self.timestamp = timestamp
        return

    def __repr__(self) -> str:
        """Prints candlestick values where defined."""
        candlestick = "(" + ", ".join(
            "{}: {}".format(key, value)
            for key, value in sorted(vars(self).items())
            if (value is not None)
        ) + ")"
        return candlestick

    def __str__(self) -> str:
        """See __repr__"""
        return self.__repr__()
