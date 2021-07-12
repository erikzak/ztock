# -*- coding: utf-8 -*-
"""
Standardizes API communication between vendors.
"""
from .client import Client
from .saxo import SaxoClient


__all__ = [
    "Client",
    "SaxoClient",
]
