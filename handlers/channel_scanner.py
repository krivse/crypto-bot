from datetime import datetime

from functions.computing import calculate_quantity
from api.google_sheet import get_auto_bot
from functions.temporary_storage import trs
from logs.logging_config import logging

from telethon import events

from api.bybit import (
    check_leverage,
    create_order,
    get_avgPrice_order,
    get_last_price,
    get_open_order,
    set_leverage,
    get_wallet_balance,
    set_trading_stop,
    cancel_all_orders, cancel_order, get_open_order_to_exit,  # get_open_order_to_exit,
)

from functions.validate import search_STP, search_coin, search_intro_word, trading_strategy


@events.register(events.NewMessage())  # from_users=[-1002090011518]  # incoming - only incoming updates
async def bybit_on(event):
    # Получаем экземпляр класса через свойство
    service = event.client.service
    # Получаем экземпляры класса через свойство
    # queue = event.client.queue
    # экземпляр WebSocker
    # ws = event.client.ws

    # Проверка времени запроса в гугл-таблицу
    if trs.check_time_google():
        # Параметры обработки данных из гугл-таблицы по заданному интервалу в секундах
        trs.google_param = get_auto_bot(service)
    rows = trs.google_param

    # id-чата отправителя
    chat_id = event.sender_id
    # Текст сообщения в нижнем регистре
    message = event.raw_text.lower()

    # Цикл по строкам
    for i in range(len(rows)):
        # Проверка колонки А:: (index 0) на соответствие id канала / проверка статуса в колонке Z:: (index 25)
        if not rows[i]:
            continue
        if int(rows[i][0]) == chat_id and int(rows[i][25]):
            logging.info(
                f'Start searching for coin from channel: {rows[i][1]}, '
                f'current time: {datetime.now().strftime("%H:%M:%S %d.%m.%Y")}'
            )

            # Колонка Y:: передаётся значение "0" для откл. /  "1" для вкл. тестового режима для API bybit (index 24)
            try:
                demo = True if int(rows[i][24]) else False
            except ValueError:
                logging.critical('For demo mode in column Y (index 24):: Value may be only 0 or 1')
                continue

            # Поиск слова / словосочетания для выхода из сделки в колонке W:: (index 22)
            exitWord = rows[i][22].lower().split('*')

            result = await search_intro_word(exitWord, message, 'column W:: (exit)')
            if result is True:
                # В колонке G:: (index 6) H:: (index 7) вводное слово для поиска монеты
                intro_coin = rows[i][6].lower().split('*') if rows[i][6] != '' else rows[i][7].lower().split('*')
                # I:: (index 8) Проверка из белого списка
                white_list = rows[i][8].strip().split('*')
                # G:: (index 9) Проверка из черного списка
                black_list = rows[i][9].strip().split('*')
                # L:: (index 11) Дополнительная обрезка монеты из сообщения
                trim_coin = rows[i][11].strip().replace('*', '|').lower() if rows[i][11] != '' else ''
                # Поиск монеты в сообщении по колонкам G H I J
                symbol = await search_coin(demo, intro_coin, white_list, black_list, message, trs, trim_coin)
                if not symbol:
                    continue
                logging.info(f'coin found to exit the deal: {symbol}')
                #await get_open_order_to_exit(testnet, symbol)
                # await cancel_all_orders(testnet, symbol)
                # await cancel_order(testnet, f'{symbol}USDT', '2b383ca5-6a6e-42ac-a12d-df4e06b100b5')
                #break
            # Поиск слова / словосочетания в сообщении по колонке С:: (index 2)
            introWord = rows[i][2].lower().split('*')

            result = await search_intro_word(introWord, message, 'column C:: (intro)')
            if result is False:
                continue

            # Поиск слова / словосочетания для прекращения обработки сообщения D:: (index 3)
            blacklist = rows[i][3].lower().split('*') if rows[i][3] != '' else ''

            result = await search_intro_word(blacklist, message, 'column D:: (blacklist)')
            if result is True:
                continue

            # Поиск параметров в колонке E:: SHORT (index 4) / I:: LONG (index 5)
            sell, buy = rows[i][4].strip().lower().split('*'), rows[i][5].strip().lower().split('*')

            side = await trading_strategy(sell, buy, message)
            if not side:
                continue

            # В колонке G:: (index 6) H:: (index 7) вводное слово для поиска монеты
            intro_coin = rows[i][6].lower().split('*') if rows[i][6] != '' else rows[i][7].lower().split('*')
            # I:: (index 8) Проверка из белого списка
            white_list = rows[i][8].strip().split('*')
            # G:: (index 9) Проверка из черного списка
            black_list = rows[i][9].strip().split('*')
            # L:: (index 11) Дополнительная обрезка монеты из сообщения
            trim_coin = rows[i][11].strip().replace('*', '|').lower() if rows[i][11] != '' else ''
            # Поиск монеты в сообщении по колонкам G H I J
            symbol = await search_coin(demo, intro_coin, white_list, black_list, message, trs, trim_coin)
            if not symbol:
                continue
            logging.info(f'coin found: {symbol}')

            # Режим для мультиордеров X:: (index 23)
            try:
                if int(rows[i][23]) == 0:
                    # Проверяется открыт ли ордeр на текущую позицию short (Sell) / long (Buy)
                    result = await get_open_order(demo, symbol)
                    # Открыт ордер в оба направления / в текущую сторону: short / long
                    if result is False:
                        if side != result:
                            continue
            except ValueError:
                logging.critical('For multiorders mode in column X (index 23):: Value may be only 0 or 1')
            # Если Y:: (index 23) != 0 ... продолжается дальнейшая обработка сообщения в режиме мультиордеров
            # Это означает, что включен режим мультиордеров, т.е. (index 23) == 1

            # Колонка U:: трейлинг стоп-лос значение в % (index 20)
            # Колонка N:: вводное слово для поиска значения стоп-лос из сообщения канала (index 13)
            # Колона P:: заранее определено значение стоп-лос для текущего канала (index 15)
            trailingStop = ''
            try:
                trailingStop = rows[i][20] if rows[i][20] != '' else ''  # трейлинг стоп-лос наивысший приоритет
                if trailingStop.isdigit():
                    logging.info(f'Set trailing-stop: {trailingStop}')
            except ValueError:
                logging.critical('For trailing-stop in column U (index 20):: Value may be only number')
            stopLoss = ''
            if trailingStop == '':  # наивысший приоритет
                stopLoss = float(rows[i][15]) if rows[i][15] != '' else ''  # стоп-лос приоритет средний
                if stopLoss == '':
                    entryWord_stopLoss = rows[i][13].strip().lower().split('*')
                    if entryWord_stopLoss != '':
                        # Приведение к типу str для отключения расчёта стоп-лоса
                        stopLoss = str(await search_STP(entryWord_stopLoss, message, 'stop-loss'))
                        if not stopLoss:
                            stopLoss = 2
                            logging.info(f'Set stop-loss: {stopLoss}')
                    else:
                        stopLoss = 2
                        logging.info(f'Set stop-loss: {stopLoss}')

            # Цели - при достижении критерия (цены) закрывается ордер
            # Колонка M:: вводное слово для поиска значения цели из сообщения канала (index 12) - наименьший приоритет
            # Колонка 0:: заранее определено значение в % для текущего канала (index 14) - наивысший приоритет
            # Колонка T:: разделитель цен "цели" (index 19)
            takeProfit = ''
            try:
                takeProfit = float(rows[i][14]) if rows[i][14] != '' else ''  # цель
                if isinstance(takeProfit, float):
                    logging.info(f'Set take-profit: {takeProfit}')
            except ValueError:
                logging.critical('Value may be only number')
            splitter = rows[i][19] if rows[i][19] != '' else ' '  # разделитель для целей колонки M:: (index 12)
            trimmer = rows[i][21] if rows[i][21] != '' else ''  # дополительная обрезка для целей V:: (index 21)
            if takeProfit == '':
                entryWord_target = rows[i][12].strip().lower().split('*')
                if entryWord_target != '':
                    takeProfit = await search_STP(entryWord_target, message, 'take-profit', splitter, trimmer)
                    if not takeProfit:
                        takeProfit = 2.0
                        logging.info(f'Set take-profit: {takeProfit}')
                else:
                    takeProfit = 2.0
                    logging.info(f'Set take-profit: {takeProfit}')

            # Создать ордер по рынку / отложенный ордер
            # В колонке K:: поле == '' - ордер по рынку / поле != '' - отложенный ордер (index10)
            entry = rows[i][10].strip().lower()  # вход по рынку / отложенный ордер
            rate_dollar = ''
            rate_percent = ''
            leverage = ''
            try:
                rate_dollar = int(rows[i][16]) if rows[i][16] != '' else ''  # ставка в $
                rate_percent = float(rows[i][17]) if rows[i][17] != '' else ''  # ставка в %
                leverage = int(rows[i][18]) if rows[i][18] != '' else ''  # плечо
            except ValueError:
                logging.critical('Value may be only number')
            balance = await get_wallet_balance(demo)  # баланс кошелька
            lastPrice = await get_last_price(demo, symbol)  # последняя цена по монете

            # Рассчитывается кол-во ордеров для покупки
            limit_orders = ''
            # Получение из временного хранилища мин. число (кол-во) для открытия ордера
            minOrderQty = trs.lotSizeFilter.get(symbol).get('minOrderQty')
            if isinstance(rate_percent, float):
                # Рассчитываем какое кол-во ордеров можно купить на % от баланса
                limit_orders = round((balance / 100 * rate_percent) / (float(minOrderQty) * lastPrice))
            elif isinstance(rate_dollar, int):
                # Рассчитываем какое кол-во ордеров можно купить на фиксированную сумму
                limit_orders = round(rate_dollar / (float(minOrderQty) * lastPrice))

            qty = await calculate_quantity(
                balance,
                rate_dollar,
                rate_percent,
                leverage,
                stopLoss,
                takeProfit,
                lastPrice,
                side
            )  # сумма ордера

            if qty.get('leverage') is not None:
                checkLeverage = await check_leverage(demo, symbol)  # проверить уставленное плечо для монеты
                if checkLeverage != qty.get('leverage'):
                    await set_leverage(demo, symbol, str(qty.get('leverage')))  # установить новое кредитное плечо

            logging.info(f'Params for order: {qty}')
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
                    firstOrderId = await create_order(
                        demo, side, symbol, quantity, stopLoss, takeProfit, positionIdx, 'Market'
                    )
                    if trailingStop.isdigit() and firstOrderId:
                        _trailingStop = await get_avgPrice_order(demo, firstOrderId, symbol, int(trailingStop), tickSize)
                        await set_trading_stop(demo, symbol, _trailingStop, positionIdx)
                else:  # отложенный ордер
                    entry_point = rows[i][10].strip().replace('*', '|').lower()  # слово для поиска цены входа
                    price = await search_STP(entry_point, message, 'price')
                    if isinstance(price, float):
                        await create_order(demo, side, symbol, quantity, stopLoss, takeProfit, positionIdx, 'Limit', price)
                    else:
                        await create_order(demo, side, symbol, quantity, stopLoss, takeProfit, positionIdx, 'Market')
            else:
                continue
