# -*- coding: utf-8 -*-
"""
Handles communication with the Interactive Brokers (IBKR) API.

Requires the IBKR Gateway to be set up, running and authenticated on the
client to work.

Installation: https://interactivebrokers.github.io/cpwebapi/
API doc: https://ndcdyn.interactivebrokers.com/api/doc.html
"""
import datetime
import logging
import urllib3
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from . import Broker
from .message import Message
from .order import Order
from .position import Position
from ..config import Config
from ..constants import LOG_NAME
from ..symbol import Symbol
from ..utils import parse_decimal


class IBKR(Broker):
    """
    Handles Interactive Brokers (IBKR) API operations.
    """
    name = "IBKRBroker"
    currency = None
    minimum_order_fee = 1
    timeout = 120
    retry_on_status_codes = [500]

    version = "v1"
    order_type_remap = {
        "market": "MKT",
        "limit": "LMT",
        "stop": "STP",
        "stop_limit": "STP_LIMIT"
    }
    _contracts = {}

    def __init__(self, config: Config):
        """
        Inits IBKR broker object using supplied config.

        The following parameters should be defined in the config:

        * account_id: required IBKR account ID
        * gateway_url: optional address to IBKR gateway, defaults to localhost
        * gateway_port: optional port used for IBKR gateway, defaults to 5000

        :param config: broker config
        :type config: Config
        """
        self.config = config
        self.account_id = config.account_id
        gateway_url = getattr(config, "gateway_url", "localhost")
        gateway_port = getattr(config, "gateway_port", 5000)
        self.root_url = f"https://{gateway_url}:{gateway_port}/{self.version}/api"

        # Init logger
        self.logger = logging.getLogger(LOG_NAME)

        # Disable localhost SSL warning
        urllib3.disable_warnings()

        # Query accounts and info
        self.accounts = self.get_accounts()
        self.logger.info("{} - Account ID is {}".format(self.name, self.account_id))
        self.logger.debug("{} - Accounts: {}".format(self.name, self.accounts))
        self.ledger = self.get_account_ledger()
        return

    def authenticate(self):
        """Authentication happens through IBKR gateway software, this does nothing."""
        return

    def get_accounts(self) -> Dict[str, str]:
        """
        Queries API for user accounts.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Account/paths/~1iserver~1accounts/get
        """
        # Query API
        url = f"{self.root_url}/iserver/accounts"
        response = self.request("GET", url)
        # Unpack accounts info
        accounts = response.json()
        return accounts

    def get_portfolio_accounts(self) -> List[Dict[str, Any]]:
        """
        Returns portfolio accounts as list of dicts.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Portfolio/paths/~1portfolio~1accounts/get
        """
        accounts_url = f"{self.root_url}/portfolio/accounts"
        response = self.request("GET", accounts_url)
        return response.json()

    def get_account_ledger(self, account_id: Optional[str] = None):
        """Fetches account info, including currency and funds.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Account/paths/~1portfolio~1{accountId}~1ledger/get

        :param account_id: optional IBKR account ID, defaults to configured account
        :type account_id: str
        """
        account_id = account_id or self.account_id

        # Get portfolio accounts, required before next request
        portfolio_accounts = self.get_portfolio_accounts()

        # Get and unpack ledger
        ledger_url = f"{self.root_url}/portfolio/{account_id}/ledger"
        response = self.request("GET", ledger_url)
        ledger = response.json()["BASE"]

        # Set account currency, funds and USD exchange rate
        self.currency = ledger["currency"]
        if (self.currency == "BASE"):
            for acct in portfolio_accounts:
                if (acct["accountId"] != self.account_id):
                    continue
                self.currency = acct.get("currency", self.currency)
                break
        self.cash_balance = parse_decimal(ledger["cashbalance"])
        self.total_value = parse_decimal(ledger["netliquidationvalue"])
        self.usd_exchange_rate = parse_decimal(ledger["exchangerate"])
        self.pnl_unrealized = parse_decimal(ledger["unrealizedpnl"])
        return ledger

    def get_contract(self, contract_id: int) -> Dict[str, Any]:
        """
        Fetches contract info from ID.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Contract/paths/~1iserver~1contract~1{conid}~1info/get
        """
        if (contract_id in self._contracts):
            return self._contracts[contract_id]
        # Define URL
        url = f"{self.root_url}/iserver/contract/{contract_id}/info"
        # Query API
        response = self.request("GET", url)
        # Cache contract info
        contract = response.json()
        self._contracts[contract_id] = contract
        return contract

    def _invalidate_portfolio_cache(self, account_id: Optional[str] = None) -> None:
        """Invalidate backend portfolio cache."""
        account_id = account_id or self.account_id
        self.logger.debug("IBKR - Invalidating backend portfolio cache")
        invalidate_url = f"{self.root_url}/portfolio/{account_id}/positions/invalidate"
        self.request("POST", invalidate_url)
        return

    def refresh(self, log_ledger: Optional[bool] = False) -> None:
        """Refresh any required info, cash balances etc."""
        self.ledger = self.get_account_ledger()
        if (log_ledger):
            self.logger.info(
                "{0} - Cash balance: {1:.2f} {2} - Total value: {3:.2f} {2} - "
                "Unrealized PnL: {4:.2f} {2}".format(
                    self.name, self.cash_balance, self.currency,
                    self.total_value, self.pnl_unrealized
                )
            )
            self.logger.debug("{} - Account {} ledger: {}".format(
                self.name, self.account_id, self.ledger
            ))
        return

    def get_live_orders(self) -> List[Order]:
        """
        Returns list of live orders.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Order/paths/~1iserver~1account~1orders/get
        """
        # Define URL
        url = f"{self.root_url}/iserver/account/orders"
        # Query API
        response = self.request("GET", url)
        # Unpack into list of Order objects
        orders = [
            Order(order["order_ref"], **order)
            for order in response.json()["orders"]
            if ("order_ref" in order)
        ]
        return orders

    def cancel_order(self, order: Order) -> Dict[str, str]:
        """
        Cancels a live order.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Order/paths/~1iserver~1account~1{accountId}~1order~1{orderId}/delete

        :param order: order to cancel
        :type order: ztock.broker.Order
        :return: order id and status message
        :rtype: dict of (str, str)
        """
        # Define URL
        url = f"{self.root_url}/iserver/account/{self.account_id}/order/{order.orderId}"
        # Delete order
        response = self.request("DELETE", url)
        # Unpack and log result
        result = response.json()
        self.logger.debug("IBKR - Order cancellation status: {}".format(result))
        return result

    def cancel_stale_orders(
            self,
            live_orders: Optional[List[Order]] = None,
            order_lifetime: Optional[int] = 120
    ) -> List[Dict[str, str]]:
        """
        Cancels any stale orders over the defined lifetime.

        :param live_orders: list of live orders to check for staleness. If not
            defined, a fresh list of live orders is fetched from the broker.
        :type live_orders: list of Order
        :param order_lifetime: max order lifetime, in seconds. Defaults to 120
        :type order_lifetime: int
        :return: list of order id and status messages
        :rtype: list of dict of (str, str)
        """
        cancelled_orders = []
        if (live_orders is None):
            live_orders = self.get_live_orders()
        for order in live_orders:
            if (order.status != "Active"):
                continue
            placed_at = datetime.datetime.fromtimestamp(int(order.id.split("_")[-1]))
            order_age = datetime.datetime.now() - placed_at
            if (order_age.total_seconds() > order_lifetime):
                self.logger.info("IBKR - Cancelling order {}".format(order))
                status = self.cancel_order(order)
                cancelled_orders.append(status)
        return cancelled_orders

    def get_positions(
            self,
            account_id: Optional[str] = None,
            page_id: Optional[int] = None,
            invalidate_cache: Optional[bool] = None
    ) -> List[Position]:
        """
        Returns list of Position objects describing open trades.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Portfolio/paths/~1portfolio~1{accountId}~1positions~1{pageId}/get

        :param account_id: IBKR account ID. Defaults to selected account
            fetched during init
        :type account_id: str
        :param page_id: used for recursively fetching next page of positions,
            defaults to first page (0)
        :type page_id: str
        :param invalidate_cache: flag for invalidating portfolio cache, only
            needs to be performed once per fetch. Defaults to True
        :type invalidate_cache: bool
        :return: list of positions
        :rtype: list of ztock.broker.Position
        """
        # Default values
        account_id = account_id or self.account_id
        page_id = page_id if (page_id is not None) else 0
        invalidate_cache = invalidate_cache if (invalidate_cache is not None) else True

        # Invalidate portfolio backend cache
        if (invalidate_cache):
            self._invalidate_portfolio_cache()
        # Get portfolio accounts, required before next request
        self.get_portfolio_accounts()

        # Define URL and send query
        url = f"{self.root_url}/portfolio/{account_id}/positions/{page_id}"
        response = self.request("GET", url)
        # Unpack response
        result = response.json()
        positions = []
        for broker_position in result:
            quantity = broker_position["position"]
            if (quantity == 0):
                continue
            contract_id = broker_position["conid"]
            contract = self.get_contract(contract_id)
            position = Position(
                id=contract_id,
                symbol=contract["local_symbol"],
                quantity=parse_decimal(quantity),
                market_value=parse_decimal(broker_position["mktValue"]),
                pnl=parse_decimal(broker_position["unrealizedPnl"]),
                # Part of broker_position kwargs:
                # currency=broker_position["currency"],
                **broker_position
            )
            positions.append(position)
        if (len(positions) > 0):
            positions.extend(self.get_positions(account_id, page_id + 1, invalidate_cache=False))
        return positions

    def get_symbol_contracts(self, symbol_name: str) -> Dict[str, Union[str, bool]]:
        """
        Searches for a symbol contract.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Contract/paths/~1iserver~1secdef~1search/post

        :param symbol_name: symbol to search for
        :type symbol_name: str
        :return: contract
        :rtype: dict of (str, [str, bool])
        """
        url = f"{self.root_url}/iserver/secdef/search"
        data = {
            "symbol": symbol_name,
        }
        response = self.request("POST", url, json=data)
        contracts = response.json()
        if (len(contracts) == 0):
            raise ValueError("IBKR - No contracts for symbol {}".format(symbol_name))
        self.logger.debug("IBKR - {} symbol contracts: {}".format(symbol_name, contracts))
        return contracts

    def place_order(
            self,
            symbol: Symbol,
            quantity: Union[int, Decimal],
            side: str,
            order_type: Optional[str] = None,
            contract_type: Optional[str] = None,
            **kwargs
    ) -> Order:
        """
        Places an order.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Order/paths/~1iserver~1account~1{accountId}~1order/post

        :param symbol: symbol to buy
        :type symbol: ztock.broker.Symbol
        :param quantity: number of stocks to buy
        :type quantity: int or Decimal
        :param side: BUY or SELL order
        :type side: str
        :param order_type: optional order type, defaults to market. Valid values are:
            * market
            * limit
            * stop
            * stop limit
        :type order_type: str
        :param contract_type: optional IBKR contract type, defaults to STK
        :type contract_type: str
        :return: order object
        :rtype: ztock.broker.Order
        """
        contract_type = contract_type or "STK"
        # Get symbol contract info
        contracts = self.get_symbol_contracts(symbol.name)
        contract = None
        for contract_info in contracts:
            for section in contract_info["sections"]:
                if (section["symbol"] != symbol.name):
                    continue
                if (section["secType"] == contract_type):
                    contract = contract_info
                    break
            if (contract):
                break

        if (contract is None):
            raise ValueError("IBKR - No {} contract found for symbol: {}".format(
                contract_type, symbol.name
            ))

        # Define payload parameters
        sec_type = f"{contract['conid']}:{contract_type}"
        contract_id = f"ztock_{side}_{symbol.name}_{int(datetime.datetime.now().timestamp())}"
        # Map order type to IBKR values
        order_type = self.order_type_remap[order_type] if (order_type is not None) else "MKT"
        # Validate quantity
        if (isinstance(quantity, Decimal) and quantity == quantity.to_integral_value()):
            quantity = int(quantity)

        # Define URL and payload
        url = f"{self.root_url}/iserver/account/{self.account_id}/order"
        data = {
            "acctId": self.account_id,
            "conid": contract["conid"],
            "secType": sec_type,
            "cOID": contract_id,
            # "parentId": contract_id,
            "orderType": order_type,
            # "listingExchange": symbol.exchange,
            # "outsideRTH": False,
            # "price": 0,
            "side": side,
            # "ticker": symbol.name,
            "tif": "DAY",
            "referrer": "ztock",
            "quantity": quantity,
            # "fxQty": 0,
            "useAdaptive": True,
            # "isCurrencyConversion": False,
            # "allocationMethod": "NetLiquidity"
        }

        # Optional parameters
        if ("exchange" in kwargs and kwargs["exchange"]):
            data["listingExchange"] = kwargs["exchange"]
        if (order_type != "MKT" and "price" in kwargs and kwargs["price"]):
            data["price"] = kwargs["price"]

        # Send request
        self.logger.debug("IBKR - {} order params: {}".format(side, data))
        response = self.request("POST", url, json=data)

        # Generate and return Order object
        result = response.json()
        messages = [
            Message(message["id"], message["message"])
            for message in result
        ]
        order = Order(contract_id, messages=messages)

        for i, message in reversed(list(enumerate(messages))):
            if (not message.content):
                continue

            # If IB warning about missing market data, confirm order
            if (any(
                    content.startswith(
                        "You are trying to submit an order without having "
                        "market data for this instrument"
                    )
                    for content in message.content
            )):
                self._send_order_reply(message, True)
                messages.pop(i)
                continue

            # Confirm market order cap price
            elif (any(
                    "<h4>Confirm Mandatory Cap Price</h4>" in content
                    for content in message.content
            )):
                self._send_order_reply(message, True)
                messages.pop(i)
                continue

        # Log any unhandled messages
        if (messages):
            self.logger.error("IBKR - Unhandled order messages: {}".format(messages))

        return order

    def _send_order_reply(self, message: Message, reply: bool) -> Dict[str, str]:
        """
        Places an order reply.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Order/paths/~1iserver~1reply~1{replyid}/post
        """
        url = f"{self.root_url}/iserver/reply/{message.id}"
        self.logger.debug("IBKR - Replying {} to message: {}".format(reply, message))
        data = {
            "confirmed": reply,
        }
        response = self.request("POST", url, json=data)
        status = response.json()[0]
        self.logger.debug("IBKR - Received status {}".format(status))
        return status

    def place_buy_order(
            self,
            symbol: Symbol,
            quantity: Union[int, Decimal],
            order_type: Optional[str] = None,
            **kwargs
    ) -> Order:
        """
        Places a buy order.

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Order/paths/~1iserver~1account~1{accountId}~1order/post

        The following keyword arguments can be passed in:

        * exchange: exchange code
        * price: order price, if not market order

        :param symbol: symbol to buy
        :type symbol: ztock.broker.Symbol
        :param quantity: number of stocks to buy
        :type quantity: int or Decimal
        :param order_type: order type, defaults to market. Valid values are:
            * market
            * limit
            * stop
            * stop limit
        :type order_type: str
        :return: order object
        :rtype: ztock.broker.Order
        """
        order = self.place_order(symbol, quantity, "BUY", order_type, **kwargs)
        return order

    def place_sell_order(
            self,
            position: Position,
            order_type: Optional[str] = None,
            **kwargs
    ) -> Order:
        """
        Places a sell order.

        The following keyword arguments can be passed in:

        https://ndcdyn.interactivebrokers.com/api/doc.html#tag/Order/paths/~1iserver~1account~1{accountId}~1order/post

        * exchange: exchange code
        * price: order price, if not market order

        :param position: position/open trade to close
        :type position: ztock.broker.Position
        :param order_type: order type, defaults to market. Valid values are:
            * market
            * limit
            * stop
            * stop limit
        :type order_type: str
        :return: order object
        :rtype: ztock.broker.Order
        """
        order = self.place_order(position.symbol, position.quantity, "SELL", order_type, **kwargs)
        return order
