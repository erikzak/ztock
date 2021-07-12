# -*- coding: utf-8 -*-
"""
Saxo Bank authentication storage.
"""
import datetime
from typing import Dict, Union

from .database import Database, Field


SCHEMA = [
    Field("access_token", "TEXT"),
    Field("token_type", "TEXT"),
    Field("expires_in", "INTEGER"),
    Field("refresh_token", "TEXT"),
    Field("refresh_token_expires_in", "INTEGER"),
    Field("base_uri", "TEXT"),
    Field("timestamp", "REAL"),
]


class SaxoDB(Database):
    """
    Handles database storage of Saxo Bank client access tokens for
    authentication between python script sessions.
    """
    def __init__(self) -> None:
        """Inits Saxo Bank token database with default name."""
        name = "saxo"
        super().__init__(name)
        self.field_names = [field.name for field in SCHEMA]
        self.date_fields = ["timestamp"]

        # Create token table if it does not exist
        self.token_table_name = "token"
        if (self.token_table_name.upper() not in [table.upper() for table in self.tables]):
            self.logger.debug("SaxoDB - Token database table does not exist, creating table")
            self.create_table(self.token_table_name, SCHEMA)
        return

    def get_token(self) -> Dict[str, Union[str, int, datetime.datetime]]:
        """Fetches Saxo token dict from SQLite database."""
        token_rows = [row for row in self.select(self.token_table_name, self.field_names)]
        if (len(token_rows) == 0):
            return {}
        token = {field.name: token_rows[0][i] for i, field in enumerate(SCHEMA)}

        for date_field in self.date_fields:
            token[date_field] = datetime.datetime.fromtimestamp(token[date_field])
        self.logger.debug("SaxoDB - Stored token: {}".format(token))
        return token

    def store_token(self, token: Dict[str, Union[str, int, datetime.datetime]]) -> None:
        """Stores Saxo token dict in SQLite database."""
        token_row = [token.get(field, None) for field in self.field_names]
        self.truncate(self.token_table_name)
        self.insert(self.token_table_name, self.field_names, [token_row])
        return
