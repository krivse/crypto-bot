import asyncio

from functions.computing import calculate_quantity
from api.google_sheet import get_auto_bot
from logs.logging_config import logging

from telethon import events

from api.bybit import check_leverage, create_order, get_avgPrice_order, get_last_price, get_open_order, set_leverage, \
    get_wallet_balance, set_trading_stop

from functions.validate import search_STP, search_coin, search_intro_word, trading_strategy


@events.register(events.NewMessage())  # from_users=[-1002090011518]  # incoming - only incoming updates
async def bybit_on(event):
    # Получаем экземпляр класса через свойство
    trs = event.client.trs
    # Получаем экземпляр класса через свойство
    queue = event.client.queue
    # экземпляр WebSocker
    ws = event.client.ws
    # Параметры обработки данных из гугл-таблицы
    rows = await asyncio.to_thread(get_auto_bot)

    # id-чата отправителя
    chat_id = event.sender_id
    # Текст сообщения в нижнем регистре
    message = event.raw_text.lower()

    for i in range(len(rows)):
        # Проверка колонки А2:: (index 0) на соответствие названия канала / проверка статуса в колонке X:: (index 23)
        if int(rows[i][0]) == chat_id and int(rows[i][23]):
            # Поиск слова / словосочетания в сообщении по колонке С:: (index 2)
            try:
                introWord = rows[i][2].lower().split('*')

                result = await search_intro_word(introWord, message, 'column C:: (intro)')
                if result is False:
                    continue
            except Exception as err:
                logging.error(err)

            # Поиск слова / словосочетания для прекращения обработки сообщения D:: (index 3)
            try:
                blacklist = rows[i][3].lower().split('*') if rows[i][3] != '' else ''

                result = await search_intro_word(blacklist, message, 'column D:: (blacklist)')
                if result is None:
                    continue
            except Exception as err:
                logging.error(err)

            # Поиск параметров в колонке H:: SHORT (index 7) / I:: LONG (index 8)
            side = ''
            try:
                sell, buy = rows[i][4].strip().lower().split('*'), rows[i][5].strip().lower().split('*')

                side = await trading_strategy(sell, buy, message)
                if not side:
                    continue
            except Exception as err:
                logging.error(err)

            # Колонка W:: передаётся значение для вкл. / откл. тестового режима для API bybit (index 21)
            testnet = True if rows[i][22] else False

            # В колонке G:: (index 6) H:: (index 7) поиск монеты /
            # I:: (index 8) Проверка из белого списка / G:: (index 9) Проверка из черного списка
            symbol = ''
            try:
                intro_coin = rows[i][6].lower().split('*') if rows[i][6] != '' else rows[i][7].split('*')
                white_list = rows[i][8].strip().lower().split('*')
                black_list = rows[i][9].strip().lower().split('*')
                trim_coin = rows[i][11].strip().lower().replace('*', '|') if rows[i][11] != '' else ''

                symbol = await search_coin(testnet, intro_coin, white_list, black_list, message, trs, trim_coin)
                if not symbol:
                    continue
                logging.info(f'coin found: {symbol}')
            except Exception as err:
                logging.error(err)

            # Проверяется открыт ли ордeр на текущую позицию short (Sell) / long (Buy)
            result = await get_open_order(testnet, symbol)
            # Открыт ордер в оба направления / в текущую сторону: short / long
            if result is False:
                if side != result:
                    continue
            # ... продолжается дальнейшая обработка сообщения

            # Колонка U:: трейлинг стоп-лос значение в % (index 20)
            # Колонка O:: вводное слово для поиска значения стоп-лос из сообщения канала (index 14)
            # Колона P:: заранее определено значение стоп-лос для текущего канала (index 15)
            trailingStop = int(rows[i][20]) if rows[i][20] != '' else ''  # трейлинг стоп-лос

            stopLoss = ''
            if trailingStop == '':  # наивысший приоритет
                try:
                    stopLoss = int(rows[i][15]) if rows[i][15] != '' else ''  # стоп-лос

                    if stopLoss == '':
                        entryWord_stopLoss = rows[i][14].strip().lower()
                        if entryWord_stopLoss != '':
                            stopLoss = await search_STP(entryWord_stopLoss, message, 'stop-loss')
                            if not stopLoss:
                                stopLoss = 2
                        else:
                            stopLoss = 2
                except Exception as err:
                    logging.error(err)

            # Цели - при достижении критерия (цены) закрывается ордер
            # Колонка M:: вводное слово для поиска значения цели из сообщения канала (index 12)
            # Колонка N:: заранее определено значение в % для текущего канала (index 13)
            # Колонка T:: разделитель цен "цели" (index 19)
            takeProfit = ''
            try:
                takeProfit = int(rows[i][13]) if rows[i][13] != '' else ''  # цель
                splitter = rows[i][19] if rows[i][19] != '' else ' '  # разделитель
                if takeProfit == '':
                    entryWord_target = rows[i][12].strip().lower().split('*')
                    if entryWord_target != '':
                        takeProfit = await search_STP(entryWord_target, message, 'take-profit', splitter)
                        if not takeProfit:
                            takeProfit = 2
                    else:
                        takeProfit = 2
            except Exception as err:
                logging.error(err)

            # Создать ордер по рынку / отложенный ордер
            # В колонке K:: поле == '' - ордер по рынку / поле != '' - отложенный ордер (index10)
            try:
                entry = rows[i][10].strip()  # вход по рынку / отложенный ордер
                rate_dollar = int(rows[i][16]) if rows[i][16] != '' else ''  # ставка в $
                rate_percent = int(rows[i][17]) if rows[i][17] != '' else ''  # ставка в %
                leverage = int(rows[i][18]) if rows[i][18] != '' else ''  # плечо
                balance = await get_wallet_balance(testnet)  # баланс кошелька
                lastPrice = await get_last_price(testnet, symbol)  # последняя цена по монете

                # Рассчитывается кол-во ордеров для покупки
                limit_orders = ''
                # Получение из временного хранилища мин. число (кол-во) для открытия ордера
                minOrderQty = trs.lotSizeFilter.get(symbol).get('minOrderQty')
                if isinstance(rate_percent, int):
                    # Рассчитываем какое кол-во ордеров можно купить на % от баланса
                    limit_orders = round((balance / 100 * rate_percent) / (float(minOrderQty) * lastPrice))
                elif isinstance(rate_dollar, int):
                    # Рассчитываем какое кол-во ордеров можно купить на фиксированную сумму
                    limit_orders = round(rate_dollar / (float(minOrderQty) * lastPrice))

                qty = await calculate_quantity(
                    balance, rate_dollar, rate_percent, leverage, stopLoss, takeProfit, lastPrice, side
                )  # сумма ордера

                if qty.get('leverage') is not None:
                    checkLeverage = await check_leverage(testnet, symbol)  # проверить уставленное плечо для монеты
                    if checkLeverage != qty.get('leverage'):
                        await set_leverage(
                            testnet, symbol, str(qty.get('leverage'))  # установить новое кредитное плечо
                        )
                if qty != {}:
                    quantity, stopLoss, takeProfit = qty.get('quantity'), qty.get('stopLoss'), qty.get('takeProfit')

                    # Выделяется доступный лимит ордеров для покупки
                    takeProfit = takeProfit if len(takeProfit) <= limit_orders else takeProfit[:limit_orders]

                    # Получение из временного хранилища мин. число (кол-во) для открытия ордера
                    minOrderQty = trs.lotSizeFilter.get(symbol).get('minOrderQty')
                    if minOrderQty.isdigit():  # мин. число - целое число
                        # кол-во монет / длину тейк-профитов = кол-во ордера, например: 100 / 3 = 3 ордера по 33,33
                        quantity = str(int(quantity / len(takeProfit)))
                    else:  # мин. число - вещественное число
                        quantity = str(round(quantity / len(takeProfit), len(minOrderQty.split('.')[1])))

                    tickSize = trs.priceFilter.get(symbol).get('tickSize')
                    if tickSize.isdigit():  # мин. число - целое число
                        tickSize = len(tickSize)
                    else:  # мин. число - вещественное число
                        tickSize = len(tickSize.split('.')[1])

                    if side == 'Buy':  # хеджирование (открытие ордера в обе стороны) / необходим для трейлинг-стоп
                        positionIdx = 1  # Buy side of hedge-mode position
                    else:
                        positionIdx = 2  # Sell side of hedge-mode position

                    if entry == '':  # вход по рынку
                        result = await create_order(
                            testnet, side, symbol, quantity, stopLoss, takeProfit, positionIdx, 'Market'
                        )
                        firstOrderId = result
                    else:  # отложенный ордер
                        entry_point = rows[i][10].strip().lower().replace('*', '|')  # слово для поиска цены входа
                        price = await search_STP(entry_point, message, 'price')
                        if isinstance(price, float):
                            result = await create_order(
                                testnet, side, symbol, quantity, stopLoss, takeProfit, positionIdx, 'Limit', price
                            )
                            firstOrderId = result
                        else:
                            result = await create_order(
                                testnet, side, symbol, quantity, stopLoss, takeProfit, positionIdx, 'Market'
                            )
                            firstOrderId = result

                    if isinstance(trailingStop, int):  # устанавливается трейлинг-стоп
                        _trailingStop = await get_avgPrice_order(
                                testnet, firstOrderId, symbol, trailingStop, tickSize
                            )
                        await set_trading_stop(testnet, symbol, _trailingStop, positionIdx)
                else:
                    continue
            except Exception as err:
                logging.error(err)
