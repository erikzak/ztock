# -*- coding: utf-8 -*-
"""
Tests for database modules.
"""
import datetime
import os
import sys

sys.path.append(os.path.realpath(os.path.dirname(os.path.dirname(__file__))))
from ztock.databases import SaxoDB


def main():
    """
    Creates database and table, stores and fetches token row.
    """
    saxo_db = SaxoDB()
    token = {
        'access_token': f'test_access_{datetime.datetime.now().timestamp()}',
        'token_type': 'Bearer',
        'expires_in': 1193,
        'refresh_token': f'test_refresh_{datetime.datetime.now().timestamp()}',
        'refresh_token_expires_in': 3593,
        'base_uri': None,
        'authentication_code': 'de300648-3594-4163-b2df-9d086db555d7',
        'timestamp': datetime.datetime(2021, 6, 21, 21, 37, 30, 755811)
    }
    # saxo_db.store_token(token)
    print(saxo_db.get_token())
    return
 

if (__name__ == "__main__"):
    main()
