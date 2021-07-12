# -*- coding: utf-8 -*-
"""
Base Order class. Unifies and keeps track of order parameters across brokers.
"""


class Order:
    """Base Order class."""
    def __init__(self, id, **kwargs):
        """
        Inits Order object with optional keyword arguments.
        """
        self.id = id
        for key, value in kwargs.items():
            if (not hasattr(self, key)):
                setattr(self, key, value)
        return

    def __repr__(self) -> str:
        """Prints order id along with available attributes."""
        return f"{vars(self)}"

    def __str__(self) -> str:
        """See __repr__"""
        return self.__repr__()
