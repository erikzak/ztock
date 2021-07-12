# -*- coding: utf-8 -*-
"""
ztock package exceptions.
"""


class AuthenticationExpiredError(Exception):
    """Exception for when all access tokens have expired, and a new login is necessary."""
    pass


class NoDataException(Exception):
    """No data status error from market data vendor."""
    pass


class UnknownExchange(Exception):
    """Unknown exchange code passed to Exchange object."""
    pass
