import time
from queue import Queue

from pybit.unified_trading import WebSocket
from typing import Union

from api.bybit import amend_order, get_open_orders
from config import config
from logs.logging_config import logging


class BybitWebSocket:
    API_KEY = config.bybit.api_key
    API_SECRET = config.bybit.api_secret
    TEST_NET = config.bybit.testnet  # Удален, нужно решить какие данные взять
    QUEUE_DATA: Union[Queue, int] = None

    def __init__(self, testnet: bool = None):
        self.testnet = testnet if testnet is not None else self.TEST_NET

    def _connect(self):
        if self.testnet:
            self.API_KEY = config.bybit.api_key_testnet
            self.API_SECRET = config.bybit.api_secret_testnet
            self.TEST_NET = self.testnet
        try:
            return WebSocket(
                testnet=self.TEST_NET,
                channel_type="private",
                api_key=self.API_KEY,
                api_secret=self.API_SECRET,
                trace_logging=False
            )
        except (KeyboardInterrupt, SystemExit):
            logging.error('Websocket disconnect')

    def execution_stream(self, queue: Queue, timeout: Union[int, float] = 1):
        self.QUEUE_DATA = queue
        connect = self._connect()
        connect.execution_stream(self._response)
        self._on(timeout)

    def _response(self, message):
        data = message.get('data')[0]

        side = data.get('side')
        symbol = data.get('symbol')
        entry_price = data.get('execPrice')
        if entry_price.isdigit():  # мин. число - целое число
            tickSize = len(entry_price)
        else:  # мин. число - вещественное число
            tickSize = len(entry_price.split('.')[1])

        new_stopLoss = ''
        order_ids = None

        if float(data.get('closedSize')) == 0:
            logging.info("when closedSize == 0")
            # новый стоп-лос равен цене входа 'execPrice'
            if side == 'Sell':
                new_stopLoss = str(round(float(entry_price) + (float(entry_price) / 100 * 1), tickSize))
            else:
                new_stopLoss = str(round(float(entry_price) - (float(entry_price) / 100 * 1), tickSize))
            order_ids = get_open_orders(testnet=self.TEST_NET, symbol=symbol, side=side)

        elif float(data.get('closedSize')) > 0:

            # новый стоп-лос равен цене продажи
            exit_price = data.get('orderPrice')
            if side == 'Sell':
                new_stopLoss = str(round(float(exit_price) + (float(exit_price) / 100 * 0.1), tickSize))
                side = 'Buy'
            else:
                new_stopLoss = str(round(float(exit_price) + (float(exit_price) / 100 * 0.1), tickSize))
                side = 'Sell'

            # Ордера по тейк-профиту в одном направлении
            order_ids = get_open_orders(testnet=self.TEST_NET, symbol=symbol, side=side)

        if order_ids is not None:
            for order_id in order_ids:  # изменить стоп-лос к ордеру
                amend_order(testnet=self.TEST_NET, symbol=symbol, orderId=order_id, stopLoss=new_stopLoss)

    @staticmethod
    def _on(timeout):
        try:
            while True:
                time.sleep(timeout)
        except (KeyboardInterrupt, SystemExit):
            logging.error('Websocket disconnect')
