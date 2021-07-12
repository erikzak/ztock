# -*- coding: utf-8 -*-
"""
Base Broker class. Can be used to subclass broker classes for specific
vendors.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Union

from .order import Order
from .position import Position
from ..clients import Client
from ..symbol import Symbol


class Broker(Client):
    """Base Broker class."""
    name = "Broker"
    currency = None
    minimum_order_fee = 0

    def refresh(self, log_ledger: bool = False):
        """Refresh any required info, cash balances etc."""
        raise NotImplementedError("Broker.refresh() not implemented")

    def get_live_orders(self) -> List[Order]:
        """Returns list of live orders."""
        raise NotImplementedError("Broker.get_live_orders() not implemented")

    def cancel_order(self, order: Order) -> Dict[str, str]:
        """
        Cancels a live order.

        :param order: order to cancel
        :type order: ztock.broker.Order
        :return: order id and status message
        :rtype: dict of (str, str)
        """
        raise NotImplementedError("Broker.cancel_order() not implemented")

    def cancel_stale_orders(
            self,
            live_orders: Optional[List[Order]] = None,
            order_lifetime: Optional[int] = 60
    ) -> List[Dict[str, str]]:
        """
        Cancels any stale orders over the defined lifetime.

        :param live_orders: list of live orders to check for staleness. If not
            defined, a fresh list of live orders is fetched from the broker.
        :type live_orders: list of Order
        :param order_lifetime: max order lifetime, in seconds. Defaults to 60
        :type order_lifetime: int
        :return: list of order id and status messages
        :rtype: list of dict of (str, str)
        """
        raise NotImplementedError("Broker.cancel_stale_orders() not implemented")

    def get_positions(self) -> List[Position]:
        """Returns list of Position objects describing open trades."""
        raise NotImplementedError("Broker.get_positions() not implemented")

    def place_buy_order(
            self,
            symbol: Symbol,
            quantity: Union[int, Decimal],
            order_type: Optional[str] = None,
            **kwargs
    ) -> Order:
        """
        Places a market price buy order.

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
        raise NotImplementedError("Broker.place_buy_order() not implemented")

    def place_sell_order(
            self,
            position: Position,
            order_type: str = None,
            **kwargs
    ) -> Order:
        """
        Places a sell order.

        The following keyword arguments can be passed in:

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
        raise NotImplementedError("Broker.place_sell_order() not implemented")
