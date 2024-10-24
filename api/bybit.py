import asyncio
from sys import prefix
from typing import List, Union

from pybit.exceptions import FailedRequestError, InvalidRequestError

from connects.bybit_session import session
from functions.temporary_storage import TemporaryRequestStorage
from logs.logging_config import logging


async def gel_all_coins(demo: bool, trs: TemporaryRequestStorage) -> set:
    """Получить все названия монет на бирже c ценой, мин. и макс. кол-вом для покупки
    и закэшировать результат на 24 часа.

    :param demo: bool. Режим демо
    :param trs: TemporaryRequestStorage. Временное хранилище запроса
    :return: Set. Список названий монет."""
    try:
        if trs.check_time(prefix='bybit'):
            response = await asyncio.to_thread(
                session(demo).get_instruments_info,
                category='linear'
            )
            logging.info(f'Request for a list of coins is successful')
            for r in response.get('result').get('list'):
                trs.names.add(r.get('baseCoin'))
                trs.lotSizeFilter.update({r.get('baseCoin'): r.get('lotSizeFilter')})
                trs.priceFilter.update({r.get('baseCoin'): r.get('priceFilter')})
                trs.leverageFilter.update({r.get('baseCoin'): r.get('leverageFilter')})
        return trs.names
    except FailedRequestError as err:
        logging.error(repr(err))


async def get_wallet_balance(demo: bool) -> float:
    """Получить баланс кошелька в паре с USDT.

    :param demo: bool. Режим демо
    :return: float. Баланс кошелька."""
    try:
        response = await asyncio.to_thread(
            session(demo).get_wallet_balance,
            accountType="UNIFIED"
        )
        coins = response.get('result').get('list')[0].get('coin')

        for coin in coins:
            if coin.get('coin') == 'USDT':
                balance = coin.get('walletBalance')
                logging.info('Balance is obtained successfully')
                return float(balance)
    except FailedRequestError as err:
        logging.error(repr(err))


async def check_leverage(demo: bool, symbol: str) -> float:
    """Получить текущее плечо для пары.

    :param demo: bool. Режим демо
    :param symbol: str. Название пары
    :return: float. Текущее плечо."""
    try:
        response = await asyncio.to_thread(
            session(demo).get_positions,
            category='linear',
            symbol=f'{symbol}USDT'
        )
        for param in response.get('result').get('list'):
            if param.get('leverage'):
                value = float(param.get('leverage'))
                logging.info(f'Leverage is {value} for {symbol}')
                return value
    except FailedRequestError as err:
        logging.error(repr(err))


async def set_leverage(demo: bool, symbol: str, leverage: str) -> None:
    """Установить плечо.

    :param demo: bool. Режим демо
    :param symbol: str. Название пары
    :param leverage: str. Плечо для установки
    :return: None. Установленное плечо."""
    try:
        await asyncio.to_thread(
            session(demo).set_leverage,
            category='linear',
            symbol=f'{symbol}USDT',
            buyLeverage=leverage,
            sellLeverage=leverage
        )
        logging.info(f'New leverage {leverage} is set to symbol {symbol}')
    except FailedRequestError as err:
        logging.error(repr(err))


async def create_order(
        demo: bool,
        side: str,
        symbol: str,
        qty: str,
        stopLoss: float,
        takeProfit: list,
        positionIdx: int,
        orderType: str,
        price: float = None
) -> str:
    """Выставить ордер по рынку / отложенный ордер.

    :param demo: bool. Режим демо
    :param side: str. Тип ордера short / long
    :param symbol: str. Название монеты, например: BTC
    :param qty: str. Кол-во, например: 0.03
    :param stopLoss: float. Предел для продажи, например: 36.702
    :param takeProfit: list. Цена и ордер, например: [36.714, 36.726, 36.736]
    :param positionIdx: int. Хеджирование (открытие ордера в обе стороны)
    :param orderType: str. Тип ордера: Market / Limit
    :param price: float. Цена ордера, например: 36.710

    :return: str. Идентификатор ордера для треейлинга (только по маркету)."""
    try:
        firstOrderId = ''
        for tp in range(len(takeProfit)):
            response = await asyncio.to_thread(
                session(demo).place_order,
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

            info = f'{orderType=} - {side=} - {symbol=} - ' \
                   f'{qty=} - {price=} - {stopLoss=} - ' \
                   f'{takeProfit[tp]=} - {orderType=} - {orderId=}'

            if response.get('retMsg') == 'OK':
                logging.info(info)
            else:
                logging.error(info)

            if tp == 0:
                firstOrderId = orderId  # забираем первый ордер для выставления trailing-stop
        return firstOrderId
    except (FailedRequestError, InvalidRequestError) as err:
        logging.error(repr(err))


async def get_open_order(demo: bool, symbol: str) -> bool | str:
    """Получить открытый ордер для проверки.

    :param demo: bool. Режим демо
    :symbol: str. Название пары
    :return: bool | str. True - нет открытого ордера.
                         False - есть открытый ордера в обе стороны.
                         str - тип открытого ордера."""
    try:
        response = await asyncio.to_thread(
            session(demo).get_open_orders,
            category='linear',
            symbol=f'{symbol}USDT'
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


async def get_last_price(demo: bool, symbol: str) -> float:
    """Получить цену на монету.

    :param demo: bool. Режим демо
    :param symbol: str. Название пары
    :return: float. Последняя цена монеты."""
    try:
        response = await asyncio.to_thread(
            session(demo).get_tickers,
            category='linear',
            symbol=f'{symbol}USDT'
        )
        price = response.get('result').get('list')[0].get('lastPrice')
        logging.info(f'Request for a list of coins is successful, last price {symbol}: {price}')
        return float(price)
    except FailedRequestError as err:
        logging.error(repr(err))


async def set_trading_stop(demo: bool, symbol: str, trailingStop: str, positionIdx: int) -> None:
    """Установить трейлинг стоп-лос.

    :param demo: bool. Режим демо
    :param symbol: str. Название пары
    :param trailingStop: str. Трейлинг стоп-лос
    :param positionIdx: int. Хедж режим 1: Buy side / 2 Sell side
    :return: None. Установленный трейлинг стоп-лос."""
    try:
        await asyncio.to_thread(
            session(demo).set_trading_stop,
            category='linear',
            symbol=f'{symbol}USDT',
            trailingStop=trailingStop,
            positionIdx=positionIdx,
        )

        logging.info(f'Set trailing stop-loss {trailingStop}')
    except FailedRequestError as err:
        logging.error(repr(err))


async def get_open_orders(demo: bool, symbol: str, side: str) -> List | None:
    """Получить открытые ордера по монете в одном направлении short / long с типом PartialStopLoss.

    :param demo: bool. Режим демо
    :param symbol: str. Название пары
    :param side: str. Направление: long / short
    :return: list. Идентификаторы открытых ордеров."""
    try:
        response = await asyncio.to_thread(
            session(demo).get_open_orders,
            category='linear', symbol=symbol
        )

        result = response.get('result').get('list')

        orderIds = []
        for r in result:
            # TODO: delete it later
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


async def get_avgPrice_order(demo: bool, orderId: str, symbol, trailingStop: int, tickSize: int) -> str:
    """Получить информацию о закрытом ордере по id и рассчитать трейлинг стоп.

    :param demo: bool. Режим демо
    :param orderId: str. Идентификатор ордера
    :param symbol: str. Название пары
    :param trailingStop: int. Трейлинг стоп-лос
    :param tickSize: int. Шаг цены
    :return: str. Стоп-лос с учетом трейлинга."""
    try:
        response = await asyncio.to_thread(
            session(demo).get_open_orders,
            category='linear',
            symbol=f'{symbol}USDT',
            orderId=orderId
        )
        result = response.get('result').get('list')

        if result:
            entry_price = float(result[0].get('avgPrice'))
            percent_summ = round(entry_price * (1 - trailingStop / 100), tickSize)
            _trailingStop = str(abs(round(entry_price - percent_summ, tickSize)))

            logging.info(f'Made a calculation for trailing stop: {_trailingStop}')
            return _trailingStop
    except FailedRequestError as err:
        logging.error(repr(err))


async def amend_order(demo: bool, symbol: str, orderId: str, stopLoss: str) -> str:
    """Изменить стоп-лос ордера."""
    try:
        response = await asyncio.to_thread(
            session(demo).amend_order,
            category='linear',
            symbol=symbol,
            orderId=orderId,
            triggerPrice=stopLoss
        )
        return response.get('retMsg')
    except FailedRequestError as err:
        logging.error(repr(err))


async def cancel_all_orders(demo: bool, symbol: str) -> str:
    """Отменить все ордера для монеты."""
    try:
        response = await asyncio.to_thread(
            session(demo).cancel_all_orders,
            category='linear',
            symbol=f'{symbol}USDT'
        )
        order_ids = [i.get('orderId') for i in response.get("result").get("list")]
        logging.info(f'All orders for {symbol} are canceled, order_ids: {order_ids}')
        return response.get('retMsg')
    except FailedRequestError as err:
        logging.error(repr(err))


async def get_open_order_to_exit(testnet: bool, symbol: str) -> str:
    """Получить открытый ордер для выхода."""
    try:
        response = await asyncio.to_thread(
            session(testnet).get_open_orders,
            category='linear',
            symbol=f'{symbol}USDT'
        )
        print(response)
        result = response.get('result').get('list')
        print(result)
    except FailedRequestError as err:
        logging.error(repr(err))


async def cancel_order(testnet: bool, symbol: str, orderId: str) -> str:
    """Отменить ордер."""
    try:
        response = await asyncio.to_thread(
            session(testnet).cancel_order,
            category='linear',
            symbol=symbol,
            orderId=orderId
        )
        return response.get('retMsg')
    except FailedRequestError as err:
        logging.error(repr(err))