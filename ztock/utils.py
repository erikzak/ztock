# -*- coding: utf-8 -*-
"""
ztock utility functions.
"""
import random
import secrets
import string
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Union

from .symbol import Symbol


# TODO: delete?
def seconds_to_days(seconds: Union[Decimal, float]) -> Decimal:
    """Converts seconds to days."""
    if (isinstance(seconds, float)):
        seconds = Decimal(seconds)
    return seconds / parse_decimal(60.0) / parse_decimal(60.0) / parse_decimal(24.0)


def parse_decimal(number: Union[int, float, str]) -> Decimal:
    """Converts number to decimal with defined number of decimal places."""
    return Decimal(Decimal(number).quantize(Decimal('.000001'), rounding=ROUND_HALF_UP))


def pick_random_symbols(
        count: int,
        exchange_symbols: Dict[str, Symbol],
        user_symbols: List[str]
) -> List[Symbol]:
    """
    Picks n random symbols from exchange that is not already in user defined
    symbol list.

    :param count: number of symbols to pick
    :type count: int
    :param exchange_symbols: all exchange symbols
    :type exchange_symbols: dict of (str, ztock.Symbol)
    :param user_symbols: already selected user symbols to avoid
    :type user_symbols: list of str
    :return: randomly selected symbols
    :rtype: list of ztock.Symbol
    """
    symbol_pool = [
        exchange_symbol
        for exchange_symbol in exchange_symbols.values()
        if (exchange_symbol.name not in user_symbols)
    ]
    if (len(symbol_pool) == 0):
        return []
    if (count > len(symbol_pool)):
        count = len(symbol_pool)
    random_symbols = random.sample([symbol for symbol in symbol_pool], count)
    return random_symbols


def generate_random_string(string_length: int = 12) -> str:
    """Generates a random string, for example for OAuth2 state parameter."""
    random_string = ''.join(
        secrets.choice(string.ascii_uppercase + string.digits)
        for _ in range(string_length)
    )
    return random_string


def pprint_number(number):
    """Returns pretty decimal representation of number with trailing 0's stripped."""
    string = str(number)
    if ("." in string):
        integer, decimal = string.split(".")
        decimal = decimal.rstrip("0")
        string = f"{integer}.{decimal}"
    return string
