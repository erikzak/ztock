# -*- coding: utf-8 -*-
"""
Base Client class. Can be any entity communicating with market data vendors
or brokers.
"""
import logging
import time
from typing import Any, Dict, Tuple

import requests

from ..config import Config
from ..constants import LOG_NAME


class Client:
    name = "Client"
    timeout = 60
    retry_on_status_codes = []
    session = requests

    """Base Client class. Should be subclassed into Market or Broker instances."""
    def __init__(self, config: Config) -> None:
        """
        Inits Client object using supplied config.

        :param config: broker/market config
        :type config: Config
        """
        self.config = config

        # Init logger
        self.logger = logging.getLogger(LOG_NAME)
        return

    def authenticate(self):
        """Authenticates with vendor."""
        raise NotImplementedError("Client.authenticate() not implemented")

    def refresh(self):
        """Refreshes client connection."""
        raise NotImplementedError("Client.refresh() not implemented")

    def request(
            self,
            operation: str,
            url: str,
            session: requests.Session = None,
            headers: Dict[str, str] = None,
            data: Dict[str, Any] = None,
            json: Dict[str, Any] = None,
            auth: Tuple[str] = None,
            retries: int = None
    ) -> requests.Response:
        """
        Sends requests HTTP request with specified operation, url, headers and
        data, along with retry handling on specific errors.

        :param operation: HTTP request type: GET, POST or DELETE
        :type operation: str
        :param url: request URL
        :type url: str
        :param session: optional requests Session, defaults to non-session requests
        :type session: request.Session
        :param headers: request headers
        :type headers: dict of (str, str)
        :param data: request payload to be handled as form-encoded data
        :type data: dict of (str, any)
        :param json: request payload to be handled as json
        :type json: dict of (str, any)
        :param auth: requests Basic authentication tuple of (username, password)
        :type auth: tuple of str
        :param retries: number of retries on errors, defaults to 2
        :type retries: int
        :return: requests response object
        :rtype: requests.Response
        """
        session = session or getattr(self, "session", requests)
        sleep_duration = 5

        if (operation == "GET"):
            response = session.get(
                url, params=data, headers=headers, auth=auth,
                timeout=self.timeout, verify=False
            )
        elif (operation == "POST"):
            response = session.post(
                url, data=data, json=json, headers=headers, auth=auth,
                timeout=self.timeout, verify=False
            )
        elif (operation == "DELETE"):
            response = session.delete(
                url, headers=headers, auth=auth,
                timeout=self.timeout, verify=False
            )

        # Check response status, retry on defined status codes
        try:
            response.raise_for_status()
        except requests.HTTPError:
            # Debug request and response error info
            request = response.request
            self.logger.debug(
                "HTTPError request: {} {}, headers: {}, params: {}, data: {}".format(
                    request.method, request.url, request.headers,
                    getattr(request, "params", None),
                    getattr(request, "data", getattr(request, "json", data or json))
                )
            )
            self.logger.debug("HTTPError response status code {}: {}".format(
                response.status_code, response.reason
            ))

            if (retries and response.status_code in self.retry_on_status_codes):
                self.logger.debug(
                    "Client: HTTP status code {} on {} {}, headers: {}, data: {}. "
                    "Retrying in {} seconds..".format(
                        response.status_code, operation, url, headers, data, sleep_duration
                    )
                )
                time.sleep(sleep_duration)
                return self.request(
                    operation=operation, url=url, session=session,
                    headers=headers, data=data, json=json, auth=auth,
                    retries=retries - 1
                )
            raise
        return response
