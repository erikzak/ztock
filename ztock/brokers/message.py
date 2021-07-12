# -*- coding: utf-8 -*-
"""
Base Message class. Unifies and keeps track of message parameters across
brokers.
"""
from typing import List, Union


class Message:
    """Base Message class."""
    def __init__(self, id: str, content: Union[List[str], str]):
        """
        Inits Message object with id and content.
        """
        self.id = id
        self.content = content if (isinstance(content, list)) else [content]
        return

    def __repr__(self) -> str:
        """Prints id and message."""
        return f"{self.id}: {self.content}"

    def __str__(self) -> str:
        """See __repr__"""
        return self.__repr__()
