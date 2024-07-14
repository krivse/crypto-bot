import asyncio
from typing import List, Set, AnyStr, Union

from pybit.exceptions import FailedRequestError, InvalidRequestError

from connects.bybit_session import session
from logs.logging_config import logging


async def gel_all_coins(testnet: bool, trs) -> Set:
    """Получить все названия монет и закэшировать результат на 24 часа."""
    try:
        if trs.check_time_bybit():
            response = await asyncio.to_thread(
                session(testnet).get_instruments_info,
                category='linear'
            )
            logging.info(f'Request for a list of coins is successful')
            for r in response.get('result').get('list'):
                trs.names.add(r.get('baseCoin'))
                trs.lotSizeFilter.update({r.get('baseCoin'): r.get('lotSizeFilter')})
                trs.priceFilter.update({r.get('baseCoin'): r.get('priceFilter')})
        return trs.names
    except FailedRequestError as err:
        logging.error(repr(err))


async def get_wallet_balance(testnet: bool) -> float:
    """Получить баланс кошелька."""

    try:
        response = await asyncio.to_thread(
            session(testnet).get_wallet_balance,
            accountType="CONTRACT"
        )
        coins = response.get('result').get('list')[0].get('coin')

        for coin in coins:
            if coin.get('coin') == 'USDT':
                balance = coin.get('walletBalance')
                logging.info('Balance is obtained successfully')
                return float(balance)
    except FailedRequestError as err:
        logging.error(repr(err))


async def check_leverage(testnet: bool, symbol: str) -> int:
    try:
        response = await asyncio.to_thread(
            session(testnet).get_positions,
            category='linear',
            symbol=f'{symbol}USDT'
        )
        for param in response.get('result').get('list'):
            if param.get('leverage'):
                value = int(param.get('leverage'))
                logging.info(f'Leverage is {value} for {symbol}')
                return value
    except FailedRequestError as err:
        logging.error(repr(err))


async def set_leverage(testnet: bool, symbol: str, leverage: str) -> AnyStr:
    try:
        response = await asyncio.to_thread(
            session(testnet).set_leverage,
            category='linear',
            symbol=f'{symbol}USDT',
            buyLeverage=leverage,
            sellLeverage=leverage
        )
        logging.info(f'New leverage {leverage} is set to symbol {symbol}')
        return response.get('retMsg')
    except FailedRequestError as err:
        logging.error(repr(err))


async def create_order(testnet: bool,
                       side: str,  # тип ордeра short / long
                       symbol: str,  # название монеты, например: BTC
                       qty: str,  # кол-во, например: 0.03
                       stopLoss: float,  # предел для продажи, например: 36.702
                       takeProfit: list,  # кол-во цен и ордеров, например: [36.714, 36.726, 36.736]
                       positionIdx: int,  # хеджирование (открытие ордера в обе стороны)
                       orderType: str,  # тип ордера, например: Market / Limit
                       price: float = None) -> AnyStr:  # цена ордера, например: 36.710
    """Выставить ордер по рынку / отложенный ордер."""
    try:
        firstOrderId = ''
        for tp in range(len(takeProfit)):
            response = await asyncio.to_thread(
                session(testnet).place_order,
                category='linear',
                symbol=f'{symbol}USDT',
                side=side,
                orderType=orderType,
                qty=qty,
                price=str(price),
                stopLoss=stopLoss,
                takeProfit=str(takeProfit[tp]),
                positionIdx=positionIdx,
                tpslMode='Partial',  # включение параметра для поддержки создания нескольких ордеров TP/SL
                isLeverage=1,  # не обращает внимание на кредитное плечо (ставка в долларах)
            )

            orderId = response.get('result').get('orderId')

            info = f'{orderType} - {side} - {symbol} - ' \
                   f'{qty} - {price} - {stopLoss} - ' \
                   f'{takeProfit[tp]} - {orderType} - {orderId}'

            if response.get('retMsg') == 'OK':
                logging.info(info)
            else:
                logging.error(info)

            if tp == 0:
                firstOrderId = orderId  # забираем первый ордер для выставления trailing-stop
        return firstOrderId
    except (FailedRequestError, InvalidRequestError) as err:
        logging.error(repr(err))


async def get_open_order(testnet: bool, symbol):
    """Получить открытый ордер для проверки."""
    try:
        response = await asyncio.to_thread(
            session(testnet).get_open_orders, category='linear', symbol=f'{symbol}USDT'
        )

        result = response.get('result').get('list')
        if not result:
            logging.info('No open orders')
            return True
        elif result:
            sides = set()
            for i in result:
                sides.add(i.get('side'))
            if len(sides) > 1:
                logging.info('Orders are opened on both sides')
                return False
            side = sides.pop()
            logging.info(f'Open one order on side {side}')
            return side
    except FailedRequestError as err:
        logging.error(repr(err))


async def get_last_price(testnet: bool, symbol: str) -> float:
    """Получить цену на монету."""
    try:
        response = await asyncio.to_thread(session(testnet).get_tickers, category='linear', symbol=f'{symbol}USDT')
        price = response.get('result').get('list')[0].get('lastPrice')
        logging.info(f'Request for a list of coins is successful, last price {symbol}: {price}')
        return float(price)
    except FailedRequestError as err:
        logging.error(repr(err))


async def set_trading_stop(testnet: bool, symbol: str, trailingStop: str, positionIdx: int) -> None:
    """Установить трейлинг стоп-лос."""
    try:
        response = await asyncio.to_thread(
            session(testnet).set_trading_stop,
            category='linear',
            symbol=f'{symbol}USDT',
            trailingStop=trailingStop,
            positionIdx=positionIdx,
        )

        logging.info(f'Set trailing stop-loss')
        return response.get('retMsg')
    except FailedRequestError as err:
        logging.error(repr(err))


def get_open_orders(testnet: bool, symbol: str, side: str) -> Union[List, None]:
    """Получить открытые ордера по монете в одном направлении short / long с типом PartialStopLoss."""
    try:
        response = session(testnet).get_open_orders(category='linear', symbol=symbol)

        result = response.get('result').get('list')

        orderIds = []
        for r in result:
            # entry_price = float(result[0].get('avgPrice'))
            # check_new_stop_loss = float(result[0].get('stopLoss'))
            # print(entry_price, check_new_stop_loss)
            # if entry_price == check_new_stop_loss:
            #     logging.info('Los stop was already installed')
            #     return
            if all([r.get('stopOrderType') == 'PartialStopLoss', r.get('side') != side]):
                orderIds.append(r.get('orderId'))

        logging.info('Orders are obtained for change of stop-loss')
        return orderIds
    except FailedRequestError as err:
        logging.error(repr(err))


async def get_avgPrice_order(testnet: bool, orderId: str, symbol, trailingStop: int, tickSize: int) -> AnyStr:
    """Получить информацию о закрытом ордере по id"""
    try:
        response = session(testnet).get_open_orders(category='linear', symbol=f'{symbol}USDT', orderId=orderId)
        result = response.get('result').get('list')

        if result:
            entry_price = float(result[0].get('avgPrice'))
            percent_summ = round(entry_price * (1 - trailingStop / 100), tickSize)
            _trailingStop = str(abs(round(entry_price - percent_summ, tickSize)))

            logging.info(f'Made a calculation for trailing stop: {_trailingStop}')
            return _trailingStop
    except FailedRequestError as err:
        logging.error(repr(err))


def amend_order(testnet: bool, symbol: str, orderId: str, stopLoss: str) -> AnyStr:
    """Изменить стоп-лос ордера."""
    try:
        response = session(testnet).amend_order(
            category='linear', symbol=symbol, orderId=orderId, triggerPrice=stopLoss
        )
        return response.get('retMsg')
    except FailedRequestError as err:
        logging.error(repr(err))
