# -*- coding: utf-8 -*-
"""
ztock SQL functionality. Handles SQLite stuff.
"""
import datetime
import logging
import os
import sqlite3
from typing import Any, Dict, Iterator, List, Tuple

from ..constants import DB_FOLDER, LOG_NAME


class Database:
    """Base Database class."""
    def __init__(self, db_name: str) -> None:
        """
        Inits Database object with given database name. Creates the database
        if it does not exist.

        :param db_name: SQLite database name
        :type db_name: str
        """
        self.logger = logging.getLogger(LOG_NAME)

        # Create database folder if it does not exist
        if (not os.path.exists(DB_FOLDER)):
            self.logger.debug("Database folder '{}' does not exist, creating folder".format(
                DB_FOLDER
            ))
            os.mkdir(DB_FOLDER)

        # Create connection (and database if it does not exist)
        self.name = db_name
        self.file_name = f"{self.name}.sqlite3"
        self.path = os.path.join(DB_FOLDER, self.file_name)
        self.conn = sqlite3.connect(self.path)  # pylint: disable=no-member

        # Get list of tables
        self.tables = [row[0] for row in self.select("sqlite_master", ["name"], "type = 'table'")]
        return

    def select(
            self, table: str, fields: List[str], where: str = None
    ) -> Iterator[Tuple[Any]]:
        """Returns a row generator for the table and fields."""
        cursor = self.conn.cursor()
        sql = f"SELECT {','.join(fields)} FROM {table}"
        if (where):
            sql += f" WHERE {where}"
        cursor.execute(sql)
        row = cursor.fetchone()
        while (row):
            yield row
            row = cursor.fetchone()
        _close_cursor(cursor)
        return

    def insert(self, table: str, fields: str, rows: List[Any]) -> None:
        """Insert rows into table."""
        cursor = self.conn.cursor()
        insert_rows = [prepare_row(row) for row in rows]
        values = ["?" for _ in rows[0]]
        sql = f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join(values)});"
        cursor.executemany(sql, insert_rows)
        self.conn.commit()
        _close_cursor(cursor)
        return

    def truncate(self, table: str) -> None:
        """Truncates defined table."""
        cursor = self.conn.cursor()
        sql = f"DELETE FROM {table};"
        cursor.execute(sql)
        self.conn.commit()
        _close_cursor(cursor)
        return

    def create_table(
            self, table_name: str, fields: Dict[str, Any]
    ) -> None:
        """
        Creates a SQLite database table with the given schema.name and list of Fields.

        :param table_name: target database table name
        :type db_name: str
        :param schema: dictionary to use to create database schema
        :type schema: dict of (str, any)
        :param without_rowid: optional flag for disabling rowid field, defaults to True
        :type without_rowid: bool
        """
        field_strings = [field.generate_sql_string() for field in fields]
        sql = f"CREATE TABLE {table_name} ({','.join(field_strings)});"
        cursor = self.conn.cursor()
        try:
            cursor.execute(sql)
            self.conn.commit()
        finally:
            _close_cursor(cursor)
        return


class Field:
    """Field info object."""
    def __init__(
            self, field_name: str, field_type: str = "TEXT",
            nullable: bool = True, primary_key: bool = False
    ):
        self.name = field_name
        self.type = field_type
        self.nullable = nullable
        self.primary_key = primary_key
        return

    def generate_sql_string(self):
        """Returns an SQL ready create field statement for a CREATE TABLE statement."""
        nullable = "NULL" if (self.nullable) else "NOT NULL"
        primary_key = "PRIMARY KEY" if (self.primary_key) else ""
        field_string = f"{self.name} {self.type} {nullable} {primary_key}".strip()
        return field_string


def _close_cursor(cursor: sqlite3.Cursor):  # pylint: disable=no-member
    """Tries to close cursor if possible."""
    try:
        cursor.close()
    except Exception:
        pass
    return


def prepare_row(row: List[Any]):
    """
    Prepares a row of table values for insert:

    - converts datetime.datetime to timestamps
    """
    for i, value in enumerate(row):
        if (isinstance(value, datetime.datetime)):
            row[i] = value.timestamp()
    return row
