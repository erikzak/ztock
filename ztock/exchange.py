# -*- coding: utf-8 -*-
"""
Exchange class for handling opening hours, exchange code remaps etc.
"""
import datetime
from typing import Optional

from pytz import timezone

from .exceptions import UnknownExchange


# Exchange opening hours in UTC, formatted as dicts with open, close and weekdays
OPENING_HOURS = {
    "NASDAQ": {
        "open": datetime.time(9, 30, 0, tzinfo=timezone("US/Eastern")),
        "close": datetime.time(16, 0, 0, tzinfo=timezone("US/Eastern")),
        "weekdays": [0, 1, 2, 3, 4],
    },
    "NYSE": {
        "open": datetime.time(9, 30, 0, tzinfo=timezone("US/Eastern")),
        "close": datetime.time(16, 0, 0, tzinfo=timezone("US/Eastern")),
        "weekdays": [0, 1, 2, 3, 4],
    },
    "OSE": {
        "open": datetime.time(7, 0, 0, tzinfo=timezone("Europe/Oslo")),
        "close": datetime.time(14, 20, 0, tzinfo=timezone("Europe/Oslo")),
        "weekdays": [0, 1, 2, 3, 4],
    },
}
# Exchange aliases
OPENING_HOURS["US"] = OPENING_HOURS["NASDAQ"]


class Exchange:
    """Base Exchange class."""
    def __init__(
            self, code: str,
            currency: Optional[str] = None, country: Optional[str] = None,
            **kwargs
    ) -> None:
        """
        Inits exchange object with exchange code.

        :param code: exchange code
        :type code: str
        :param currency: optional exchange currency
        :type currency: str
        :param country: two-letter country code
        :type country: str
        """
        self.code = code
        self.currency = currency
        self.country = country
        self.opening_hours = OPENING_HOURS.get(code, None)

        for key, value in kwargs.items():
            if (not hasattr(self, key)):
                setattr(self, key, value)
        return

    def is_open(self) -> bool:
        """Returns flag for if exchange is open for trading or not."""
        if (self.opening_hours is None):
            raise UnknownExchange("Unknown opening hours for exchange: {}".format(self.code))
        now = datetime.datetime.now(tz=self.opening_hours["open"].tzinfo)
        # Check weekday
        weekday = now.weekday()
        if (weekday not in self.opening_hours["weekdays"]):
            return False
        # Check time
        if (self.opening_hours["open"] <= now.timetz() < self.opening_hours["close"]):
            return True
        return False
