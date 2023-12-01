import logging
from typing import Dict


async def calculate_quantity(
        balance: float,
        r_dollar: [str, int],
        r_percent: [str, int],
        leverage: [str, int],
        stopLoss: [str, int, float],
        takeProfit: [int, [float]],
        lastPrice: [float],
        side: str
) -> Dict:
    """
    Сумма входа. Ставка$ работает сама по себе. Ставка% и Плечо работают в паре.
    Если заполнены все 3 колонки, приоритет на Ставка%, потом смотрит Плечо.
    Если плечо не указано, входит с 20 плечом.
    20 плечо пусть будет по умолчанию.

    Пример. Банк 100$. Если указано Ставка$, то входит на 20$. Реальный вход у него получается на 1$ с 20 плечом.
    Если указана Ставка% на 1%, то входит по умолчанию с 20 плечом на 1%. Это также получается на 1$ с 20 плечом на 20$.
    :param balance: int баланс кошелька
    :param r_dollar: int ставка в долларах
    :param r_percent: int ставка в процентах
    :param leverage: int кредитное плечо
    :param stopLoss: int % от суммы / цена из сообщения
    :param takeProfit: int % от суммы / цена из сообщения
    :param lastPrice: последняя цена на бирже
    :param side: стратегия торговли
    :return: dict {'quantity': float, 'leverage': int, 'stopLoss': float, take_profit: list[float]}
    """
    try:
        if not isinstance(stopLoss, str):  # установлен трейлинг для стоп-лос
            if isinstance(stopLoss, int):  # Расчёт стоп-лос от процента
                if side == 'Buy':
                    stopLoss = round(lastPrice - (lastPrice / 100 * stopLoss), 4)
                else:
                    stopLoss = round(lastPrice + (lastPrice / 100 * stopLoss), 4)
    except (TypeError, ValueError) as err:
        logging.error(err)
    try:
        if isinstance(takeProfit, int):  # Расчёт тейк-профит от процента
            if side == 'Buy':
                takeProfit = [round(lastPrice + (lastPrice / 100 * takeProfit), 4)]
            else:
                takeProfit = [round(lastPrice - (lastPrice / 100 * takeProfit), 4)]
    except (TypeError, ValueError) as err:
        logging.error(err)
    try:
        if all([isinstance(r_dollar, int), isinstance(r_percent, int), isinstance(leverage, int)]):
            try:
                summ = balance / 100 * r_percent
                quantity = summ / lastPrice
                return {'quantity': quantity, 'leverage': leverage, 'stopLoss': stopLoss, 'takeProfit': takeProfit}
            except (TypeError, ValueError) as err:
                logging.error(err)
        elif all([isinstance(r_percent, int), isinstance(leverage, int)]):
            try:
                summ = balance / 100 * r_percent
                quantity = summ / lastPrice
                return {'quantity': quantity, 'leverage': leverage, 'stopLoss': stopLoss, 'takeProfit': takeProfit}
            except (TypeError, ValueError) as err:
                logging.error(err)
        elif isinstance(r_percent, int):
            try:
                summ = balance / 100 * r_percent
                quantity = summ / lastPrice
                return {'quantity': quantity, 'leverage': 20, 'stopLoss': stopLoss, 'takeProfit': takeProfit}
            except (TypeError, ValueError) as err:
                logging.error(err)
        elif isinstance(r_dollar, int):
            try:
                quantity = r_dollar / lastPrice
                return {'quantity': quantity, 'leverage': leverage, 'stopLoss': stopLoss, 'takeProfit': takeProfit}
            except (TypeError, ValueError) as err:
                logging.error(err)
        else:
            return {}
    except Exception as err:
        logging.error(err)
