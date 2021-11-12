# -*- coding: utf-8 -*-
"""
Handles communication with Saxo Bank's OpenAPI.

Requires an OpenAPI app with a connected Saxo Bank user.

Overview: https://www.developer.saxo/openapi/learn
API doc: https://www.developer.saxo/openapi/referencedocs
"""
import datetime
import time
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from .order import Order
from .position import Position
from ..clients.saxo import SaxoClient
from ..config import Config
from ..symbol import Symbol
from ..utils import parse_decimal


class SaxoBroker(SaxoClient):
    """
    Handles Saxo Bank OpenAPI operations.
    """
    name = "SaxoBroker"
    currency = None
    minimum_order_fee = 7
    timeout = 60
    retry_on_status_codes = []

    order_type_remap = {
        "market": "Market",
        "limit": "Limit",
        "stop": "Stop",
        "stop_limit": "StopLimit"
    }

    def __init__(self, config: Config):
        """
        Inits Saxo Bank broker object using supplied config.

        :param config: broker config
        :type config: Config
        """
        super().__init__(config)

        # Get account info and balance
        self.get_account()
        self.client_key = self.account["ClientKey"]
        self.account_key = self.account["AccountKey"]
        self.balance = self.get_account_balance()
        self.logger.info("{} - ClientKey: {} - AccountKey: {}".format(
            self.name, self.client_key, self.account_key
        ))
        return

    def get_account(self) -> None:
        """
        Queries API for logged in user account.

        https://www.developer.saxo/openapi/referencedocs/port/v1/users/getuser/24acd0f6657d7f2a34f4a37ccad185f7
        """
        # Query API for user
        user_url = f"{self.root_url}/port/v1/users/me"
        response = self.request("GET", user_url)
        self.user = response.json()

        # Query API for account
        account_url = f"{self.root_url}/port/v1/accounts/me"
        response = self.request("GET", account_url)
        self.account = response.json()["Data"][0]

        self.logger.debug("{} - Current user: {}".format(self.name, self.user))
        self.logger.debug("{} - Current account: {}".format(self.name, self.account))
        return

    def get_account_balance(self) -> Dict[str, Any]:
        """Fetches account info, including currency and funds.

        https://www.developer.saxo/openapi/referencedocs/port/v1/balances/getbalance/9f4b3d9066a318235b25616bb21a672e

        :param account_id: optional IBKR account ID, defaults to configured account
        :type account_id: str
        """
        # Get and unpack balance
        balance_url = f"{self.root_url}/port/v1/balances/me"
        params = {
            "AccountKey": self.account_key,
            "ClientKey": self.client_key,
        }
        response = self.request("GET", balance_url, data=params)
        self.balance = response.json()

        # Set account currency, funds and USD exchange rate
        self.currency = self.balance["Currency"]
        self.cash_balance = parse_decimal(self.balance["CashBalance"])
        self.total_value = parse_decimal(self.balance["TotalValue"])
        return self.balance

    def refresh(self, log_ledger: Optional[bool] = False) -> None:
        """Refresh any required info, cash balances etc."""
        super().refresh()
        self.balance = self.get_account_balance()
        if (log_ledger):
            net_positions = self.get_net_positions()
            pnl = sum([position.pnl * position.exchange_rate for position in net_positions])
            self.logger.info(
                "{0} - Cash balance: {1:.2f} {2} - Total value: {3:.2f} {2} - "
                "Unrealized PnL: {4:.2f} {2}".format(
                    self.name, self.cash_balance, self.currency, self.total_value, pnl
                )
            )
            self.logger.debug("{} - Balance: {}".format(self.name, self.balance))
        return

    def get_live_orders(self) -> List[Order]:
        """
        Returns list of live orders.

        https://www.developer.saxo/openapi/referencedocs/port/v1/orders/getopenorders/cae24349737ea6fef4f0e6d9c477794e
        """
        # Define URL
        url = f"{self.root_url}/port/v1/orders/me"
        params = {
            "$top": 500,
        }
        # Query API
        response = self.request("GET", url, data=params)
        # Unpack into list of Order objects
        result = response.json()
        orders = [
            Order(order["OrderId"], **order)
            for order in result["Data"]
        ]
        while (result.get("__next", None)):
            result = self.request("GET", result["__next"]).json()
            orders.extend([
                Order(order["OrderId"], **order)
                for order in result["Data"]
            ])
        return orders

    def cancel_order(self, order: Union[Order, List[Order]]) -> Dict[str, str]:
        """
        Cancels a live order.

        https://www.developer.saxo/openapi/referencedocs/trade/v2/orders/cancelorder/a1fd2fffa62f21901f23318f65fe8147

        :param order: order to cancel (or list of orders)
        :type order: ztock.broker.Order
        :return: order id and status message
        :rtype: dict of (str, str)
        """
        orders = order if (isinstance(order, list)) else [order]
        # Define URL
        order_string = ",".join([str(order.id) for order in orders])
        url = f"{self.root_url}/trade/v2/orders/{order_string}/?AccountKey={self.account_key}"
        # Delete order
        response = self.request("DELETE", url)
        # Unpack and log result
        result = response.json()
        self.logger.debug("{} - Order(s) cancelled: {}".format(self.name, result))
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
        :rtype: list of dict of ztock.broker.Order
        """
        cancelled_orders = []
        if (live_orders is None):
            live_orders = self.get_live_orders()
        for order in live_orders:
            if (order.Status != "Working"):
                continue
            placed_at = self._parse_utc_datestring(order.OrderTime)
            order_age = datetime.datetime.utcnow() - placed_at
            if (order_age.total_seconds() > order_lifetime):
                self.logger.info("{} - Cancelling stale ({} s) order {}".format(
                    self.name, order_age.total_seconds(), order
                ))
                cancelled_orders.append(order)
        if (cancelled_orders):
            self.cancel_order(cancelled_orders)
        return cancelled_orders

    def get_positions(self) -> List[Position]:
        """
        Returns list of Position objects.

        https://www.developer.saxo/openapi/referencedocs/port/v1/positions/getpositions/b6d549a50a5f35244806aaa0554d6eae

        :return: list of positions
        :rtype: list of ztock.broker.Position
        """
        # Define URL and params, then send query
        url = f"{self.root_url}/port/v1/positions/me"
        params = {
            "$top": 500,
        }
        response = self.request("GET", url, data=params)
        # Unpack response
        result = response.json()
        positions = []
        for broker_position in result["Data"]:
            position = self._unpack_position(broker_position)
            if (position.quantity == 0):
                continue
            positions.append(position)
        # Get next batch (if __next url defined)
        while (result.get("__next", None)):
            result = self.request("GET", result["__next"]).json()
            for broker_position in result["Data"]:
                position = self._unpack_position(broker_position)
                if (position.quantity == 0):
                    continue
                positions.append(position)
        return positions

    def get_net_positions(self) -> List[Position]:
        """
        Returns list of net Position objects.

        https://www.developer.saxo/openapi/referencedocs/port/v1/netpositions/getnetpositions/77f81ee9488691ec98679a830bb738c4

        :return: list of net positions
        :rtype: list of ztock.broker.Position
        """
        # Define URL and params, then send query
        url = f"{self.root_url}/port/v1/netpositions/me"
        params = {
            "$top": 500,
        }
        response = self.request("GET", url, data=params)
        # Unpack response
        result = response.json()
        positions = []
        for broker_position in result["Data"]:
            position = self._unpack_position(broker_position, net_position=True)
            if (position.quantity == 0):
                continue
            positions.append(position)
        # Get next batch (if __next url defined)
        while (result.get("__next", None)):
            result = self.request("GET", result["__next"]).json()
            for broker_position in result["Data"]:
                position = self._unpack_position(broker_position, net_position=True)
                if (position.quantity == 0):
                    continue
                positions.append(position)
        return positions

    def _unpack_position(
            self, position_dict: Dict[str, Any], net_position: bool = False
    ) -> Position:
        """Unpacks Saxo Bank OpenAPI's position dict into ztock Position instances."""
        if (net_position):
            if ("SinglePosition" in position_dict):
                position_dict = position_dict["SinglePosition"]
            base = position_dict["NetPositionBase"]
            view = position_dict["NetPositionView"]
            position_id = position_dict["NetPositionId"]
        else:
            base = position_dict["PositionBase"]
            view = position_dict["PositionView"]
            position_id = position_dict["PositionId"]
        quantity = parse_decimal(base["Amount"])
        if (base.get("ExternalReference", None)):
            symbol_name = base["ExternalReference"].split("_")[2]
        else:
            symbol_name = position_dict["NetPositionId"].split("_")[0].split(":")[0]
        market_value = parse_decimal(view["CurrentPrice"]) * quantity
        exchange_rate = parse_decimal(view["ConversionRateCurrent"])
        position = Position(
            id=position_id,
            symbol=symbol_name,
            quantity=quantity,
            market_value=market_value,
            pnl=parse_decimal(view["ProfitLossOnTrade"]),
            currency=view["ExposureCurrency"],
            exchange_rate=exchange_rate,
            **position_dict
        )
        return position

    def place_order(
            self,
            symbol: Symbol,
            quantity: Union[int, Decimal],
            side: str,
            order_type: Optional[str] = None,
            **kwargs
    ) -> Order:
        """
        Places an order.

        https://www.developer.saxo/openapi/referencedocs/trade/v2/orders/placeorder/6c537dd1a311860be1ea9d8a1db334bf

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
        :return: order object
        :rtype: ztock.broker.Order
        """
        # Make sure we have symbol info from Saxo Bank
        if (not hasattr(symbol, "Identifier")):
            symbol = self.lookup_symbol(symbol.name)
        # TODO: Remove this? Not necessary atm
        # Get symbol details
        # details = self.get_symbol_details(symbol)
        # if (details is None):
        #     raise ValueError("{} - No details found for symbol: {}".format(symbol.name))

        # Define custom client ID
        custom_id = f"ztock_{side}_{symbol.name}_{int(datetime.datetime.now().timestamp())}"
        # Map order type to Saxo Bank values
        order_type = self.order_type_remap.get(order_type, order_type)
        if (order_type is None):
            order_type = "Market"
        # Validate quantity
        if (isinstance(quantity, Decimal) and quantity == quantity.to_integral_value()):
            quantity = int(quantity)

        # Define URL and payload
        url = f"{self.root_url}/trade/v2/orders"
        data = {
            "AccountKey": self.account_key,
            "Amount": quantity,
            "ExternalReference": custom_id,
            "AssetType": symbol.AssetType,
            "BuySell": side.title(),
            "ManualOrder": True,
            "OrderDuration": {
                "DurationType": "DayOrder",
            },
            "OrderType": order_type,
            "Uic": symbol.Identifier,
        }

        # Optional parameters
        price = kwargs.get("price", None)
        if (order_type != "Market" and price):
            if (order_type == "StopLimit"):
                data["StopLimitPrice"] = price
            else:
                data["OrderPrice"] = price

        # Send request
        self.logger.debug("{} - {} order params: {}".format(self.name, side, data))
        response = self.request("POST", url, json=data)

        # Generate and return Order object
        result = response.json()
        orders = Order(result["OrderId"], **result)

        # Sleep 1 sec to avoid rate limit issues
        time.sleep(1)

        return orders

    def place_buy_order(
            self,
            symbol: Symbol,
            quantity: Union[int, Decimal],
            order_type: Optional[str] = None,
            **kwargs
    ) -> Order:
        """
        Places a buy order.

        https://www.developer.saxo/openapi/referencedocs/trade/v2/orders/placeorder/6c537dd1a311860be1ea9d8a1db334bf

        The following keyword arguments can be passed in:

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

        https://www.developer.saxo/openapi/referencedocs/trade/v2/orders/placeorder/6c537dd1a311860be1ea9d8a1db334bf

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
