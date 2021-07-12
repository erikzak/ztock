# -*- coding: utf-8 -*-
"""
Saxo Bank base client. Handles authentication and storing tokens in
authentication database.

https://www.developer.saxo
"""
import datetime
import logging
import time
import urllib3
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse

import pytz
import requests

from .client import Client
from ..config import Config
from ..constants import LOG_NAME
from ..databases import SaxoDB
from ..exceptions import AuthenticationExpiredError
from ..exchange import Exchange
from ..symbol import Symbol
from ..utils import generate_random_string


class SaxoClient(Client):
    """
    Saxo Client subclass.
    """
    name = "Saxo"

    sim_urls = {
        "instruments": "https://gateway.saxobank.com/sim/openapi/ref/v1/instruments",
        "instrument_details": "https://gateway.saxobank.com/sim/openapi/ref/v1/instruments",
        "info_price": "https://gateway.saxobank.com/sim/openapi/trade/v1/infoprices",
        "charts": "https://gateway.saxobank.com/sim/openapi/chart/v1/charts",
        "place_order": "https://gateway.saxobank.com/sim/openapi/trade/v2/orders",
        "user": "https://gateway.saxobank.com/sim/openapi/port/v1/users/me",
        "account": "https://gateway.saxobank.com/sim/openapi/port/v1/accounts/me",
        "balance": "https://gateway.saxobank.com/sim/openapi/port/v1/balances/me",
        "my_orders": "https://gateway.saxobank.com/sim/openapi/port/v1/orders/me",
    }
    live_urls = {
        "instruments": "https://gateway.saxobank.com/openapi/ref/v1/instruments",
        "instrument_details": "https://gateway.saxobank.com/openapi/ref/v1/instruments",
        "info_price": "https://gateway.saxobank.com/openapi/trade/v1/infoprices",
        "charts": "https://gateway.saxobank.com/openapi/chart/v1/charts",
        "place_order": "https://gateway.saxobank.com/openapi/trade/v2/orders",
        "user": "https://gateway.saxobank.com/openapi/port/v1/users/me",
        "account": "https://gateway.saxobank.com/openapi/port/v1/accounts/me",
        "balance": "https://gateway.saxobank.com/openapi/port/v1/balances/me",
        "my_orders": "https://gateway.saxobank.com/openapi/port/v1/orders/me",
    }
    _token = None
    _instruments = {}

    def __init__(self, config: Config) -> None:
        """
        Inits Saxo object using supplied config.

        Config must contain the following parameters:
            * app_key
            * app_secret
            * redirect_uri

        You get these when registering a user for Saxo Bank's OpenAPI and
        connecting your account to the API user.

        A sim_mode key with a boolean value can also be present. If True, all
        relevant requests will be made to SIM endpoints.

        :param config: market config
        :type config: Config
        """
        # Store config
        self.config = config
        # Init SQLite database for access tokens
        self._db = SaxoDB()
        # Disable SSL warnings
        urllib3.disable_warnings()

        # Config parameters
        self.app_key = config.app_key
        self.app_secret = config.app_secret
        self.redirect_uri = config.redirect_uri
        self.sim_mode = getattr(config, "sim_mode", False)

        # Define URLs
        if (self.sim_mode):
            self.root_url = "https://gateway.saxobank.com/sim/openapi"
            self.token_url = "https://sim.logonvalidation.net/token"
            self.auth_url = "https://sim.logonvalidation.net/authorize"
        else:
            self.root_url = "https://gateway.saxobank.com/openapi"
            self.token_url = "https://live.logonvalidation.net/token"
            self.auth_url = "https://live.logonvalidation.net/authorize"

        # Get logger
        self.logger = logging.getLogger(LOG_NAME)

        # Start requests session
        self.session = requests.Session()

        # Authenticate
        self.authenticate(error_on_reauth=False)
        return

    def authenticate(self, error_on_reauth: Optional[bool] = True) -> None:
        """
        Checks if stored access tokens are valid. Init OAuth2 authentication
        flow if tokens do not exist or have expired.

        :param error_on_reauth: flag for raising AuthenticationExpiredError
            when reauthentication is required, if False logs a warning.
            Defaults to True
        :type error_on_reauth: bool
        """
        # Get token from database, if not in memory
        if (self._token is None):
            self._token = self._db.get_token()
            self._set_access_token_header()
        # Validate access/refresh token if stored. Init authentication flow if expired/missing
        if (self._token):
            if (self._validate_tokens()):
                return

        try:
            self._token = self._authenticate_oauth2()
            self.logger.debug("{}' - Storing new token: {}".format(self.name, self._token))
            self._db.store_token(self._token)
        except AuthenticationExpiredError:
            if (error_on_reauth):
                raise
            self.logger.warning("{} - Authorization required".format(self.name))
            return

        return

    def refresh(self) -> None:
        """Validates access tokens and initiates new authentication if expired."""
        self._validate_tokens()
        return

    def lookup_symbol(self, symbol_name: str) -> Symbol:
        """
        Searches for a given symbol, returns best match.

        https://www.developer.saxo/openapi/referencedocs/ref/v1/instruments/getsummaries/6e8602a4943e270d01ada208c8b26770

        :param symbol_name: symbol to search for
        :type symbol_name: str
        :return: symbol object
        :rtype: ztock.broker.Symbol
        """
        # Check if previously returned
        if (symbol_name in self._instruments):
            return self._instruments[symbol_name]
        # Define URL
        url = f"{self.root_url}/ref/v1/instruments"
        # Generate and send request with payload
        params = {
            "Keywords": symbol_name,
        }
        response = self.session.get(url, params=params)
        # Unpack result and create Symbol to return
        symbol_infos = response.json()
        symbol = self._unpack_symbol(symbol_infos["Data"][0])
        self._instruments[symbol_name] = symbol
        return symbol

    def _unpack_symbol(self, symbol_dict: Dict[str, Any]) -> None:
        """Unpacks API response symbol info dict to Symbol instance."""
        symbol_name = symbol_dict["Symbol"].split(":")[0]
        symbol = Symbol(
            symbol_name,
            display_symbol=symbol_dict["Symbol"],
            currency=symbol_dict.get("CurrencyCode", None),
            exchange=symbol_dict.get("ExchangeId", None),
            **symbol_dict
        )
        return symbol

    def request(
            self,
            operation: str,
            url: str,
            session: requests.Session = None,
            headers: Dict[str, str] = None,
            data: Dict[str, Any] = None,
            json: Dict[str, Any] = None,
            auth: Tuple[str] = None,
            retries: int = None,
            authenticate: bool = True
    ) -> requests.Response:
        """Extends base request with exception handling for stale token or reauthentication."""
        # Validate tokens, and reauthenticate if necessary
        if (authenticate):
            self.authenticate()
        try:
            # Pass on request to super
            response = super().request(
                operation=operation, url=url, session=session, headers=headers,
                data=data, json=json, auth=auth, retries=retries
            )

            # If rate limit error, wait for two minutes and retry
            if (self._request_has_rate_limit_error(response)):
                time.sleep(120)
                return super().request(
                    operation=operation, url=url, session=session, headers=headers,
                    data=data, json=json, auth=auth, retries=retries
                )

        # Exception handling
        except requests.HTTPError as error:
            response = error.response

            # If unauthorized, try to reauthenticate
            if (response.status_code == 401):
                self.logger.info(
                    "{} - HTTP 401: Invalidating tokens and initiating "
                    "reauthentication".format(self.name)
                )
                self._token = {}
                self.authenticate()
                return super().request(
                    operation=operation, url=url, session=session, headers=headers,
                    data=data, json=json, auth=auth, retries=retries
                )

            # If rate limit error, wait for two minutes and retry
            elif (response.status_code == 429):
                self.logger.warning(
                    "{} - Rate limit reached, sleeping for 2 minutes before retry..".format(self.name)
                )
                time.sleep(120)
                return super().request(
                    operation=operation, url=url, session=session, headers=headers,
                    data=data, json=json, auth=auth, retries=retries
                )

            raise

        return response

    def _request_has_rate_limit_error(self, response: requests.Response) -> bool:
        """Checks if response contains rate limit error message."""
        try:
            result = response.json()
            if (result["ErrorCode"] == "RateLimitExceeded"):
                return True
        except Exception:
            pass
        return False

    def get_exchanges(self) -> Dict[str, int]:
        """
        Returns a dict of exchange code keys and info dict values, including ID.

        https://www.developer.saxo/openapi/referencedocs/ref/v1/exchanges
        """
        url = f"{self.root_url}/ref/v1/exchanges"
        response = self.request("GET", url)
        # Unpack list of exchanges
        results = response.json()
        exchanges = {}
        for exchange_info in results["Data"]:
            exchange = Exchange(
                code=exchange_info["ExchangeId"],
                currency=exchange_info["Currency"],
                country=exchange_info["CountryCode"]
            )
            exchanges[exchange.code] = exchange
        return exchanges

    def _authenticate_oauth2(self) -> Dict[str, Union[str, int, datetime.datetime]]:
        """
        Authenticates with Saxo using OAuth2. Requires the user to open a
        authorization URL, log in and paste the callback URL back into the
        command line interface.

        :return: access token
        :rtype: str
        """
        self._state = generate_random_string()
        params = {
            "response_type": "code",
            "client_id": self.app_key,
            "state": self._state,
            "redirect_uri": self.redirect_uri,
        }
        # Prepare request URL
        request = requests.Request('GET', self.auth_url, params=params)
        print(f"Authentication URL:\n\n{request.prepare().url}\n")
        # Ask user for redirection URL
        authorization_url = input("Paste redirect URL: ")
        # TODO: Implement Django/Flask login
        # raise AuthenticationExpiredError(
        #     "{} - Access and refresh tokens expired, "
        #     "new authorization required".format(self.name)
        # )

        # Unpack authorization code from redirect URL parameters
        url_params = parse_qs(urlparse(authorization_url).query)
        if (url_params["state"][0] != self._state):
            raise ValueError(
                "{} - Response state ({}) does not match request state ({})".format(
                    self.name, url_params["state"][0], self._state
                )
            )
        auth_code = url_params["code"][0]
        # Exchange code for access token
        self._token = self._fetch_token_oauth2(auth_code)
        return self._token

    def _fetch_token_oauth2(self, auth_code: str) -> Dict[str, Union[str, int, datetime.datetime]]:
        """
        Fetches token from authentication endpoint.

        :param auth_code: authorization code
        :type auth_code: str
        """
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
            "code": auth_code,
        }
        self.logger.debug("{} - Fetching new access token with params: {}".format(self.name, data))

        response = requests.post(
            self.token_url, headers=headers, data=data, auth=(self.app_key, self.app_secret)
        )
        response.raise_for_status()
        self._token = response.json()
        self._token["timestamp"] = datetime.datetime.now()
        self._set_access_token_header()
        return self._token

    def _refresh_token(self) -> Dict[str, Union[str, int, datetime.datetime]]:
        """Refreshes access token using refresh token."""
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self._token["refresh_token"],
            "redirect_uri": self.redirect_uri,
        }
        self.logger.debug("{} - Refreshing access token with params: {}".format(self.name, data))

        response = self.request(
            "POST", self.token_url, headers=headers, data=data,
            auth=(self.app_key, self.app_secret), authenticate=False
        )
        self._token = response.json()
        self._token["timestamp"] = datetime.datetime.now()
        self._set_access_token_header()
        return self._token

    def _validate_tokens(self) -> bool:
        """Validates access tokens. Returns a boolean stating if access tokens are valid."""
        # Check if stored token has timestamp
        token_timestamp = self._token.get("timestamp", None)
        if (not token_timestamp):
            self.logger.debug("{} - Invalid tokens, timestamp missing: {}".format(
                self.name, self._token
            ))
            return False

        # Get current time and calculate token age
        now = datetime.datetime.now()
        token_age = (now - token_timestamp).seconds

        # Check if access token is still valid
        if (token_age < self._token["expires_in"]):
            return True

        # Check if refresh token is still valid. If yes, fetch new access token
        if (token_age >= self._token["refresh_token_expires_in"]):
            self.logger.debug("{} - Invalid tokens, access and refresh tokens expired: {}".format(
                self.name, self._token
            ))
            return False

        # Refresh access token
        self.logger.debug(
            "{} - Access token expired ({} s > {} s), fetching new with "
            "refresh token..".format(self.name, token_age, self._token["expires_in"])
        )
        self._refresh_token()
        return True

    def _set_access_token_header(self):
        """Updates header with access token."""
        access_token = self._token.get("access_token", "")
        token_type = self._token.get("token_type", "Bearer")
        header = "Authorization"
        value = f"{token_type} {access_token}"
        self.logger.debug("{} - Setting {} to {}".format(self.name, header, value))
        self.session.headers.update({
            header: value,
        })
        return

    def _parse_utc_datestring(self, datestring: str):
        """Parses UTC datestrings returned by Saxo Bank's OpenAPI."""
        timestamp = datetime.datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S.%fZ")
        timestamp.replace(tzinfo=pytz.utc)
        return timestamp
