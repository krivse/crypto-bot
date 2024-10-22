from logs.logging_config import logging
import re
from re import search

from api.bybit import gel_all_coins


async def search_intro_word(searchWord, message, value_column) -> bool:
    for sm in range(len(searchWord)):
        if search(searchWord[sm], message):
            logging.info(f'The introductory word is found in the {value_column}: {searchWord[sm]}')
            break
    else:
        logging.info(f'The introductory word is not found in the {value_column}: {searchWord}')
        return False
    return True


async def trading_strategy(sell, buy, message) -> bool | str:
    if '' in sell and '' in buy:
        logging.warning(f'Both SHORT and LONG cannot be empty')
        return False
    for short in sell:
        if short == '':
            logging.info(f'SHORT not found')
            continue
        if search(short, message):
            logging.info(f'SHORT found')
            return 'Sell'
    for long in buy:
        if long == '':
            logging.info(f'LONG not found')
            continue
        elif search(long, message):
            logging.info(f'LONG found')
            return 'Buy'
    return False


async def search_coin(demo, intro_coin, white_list, black_list, message, trs, trim_coin) -> bool | str:
    logging.info(f'Search for an input word for searching for coins: {intro_coin}')
    for ic in intro_coin:
        if search(ic, message):
            logging.info(f'The introductory word is found for the next process to search the coin: {ic}')
            try:
                trim_msg = re.split('\s', message)
                logging.info(f'Trim the introductory word: {trim_msg}')
                if trim_coin != '':
                    trim_coin = f'{trim_coin}|'
                for i in range(len(trim_msg)):
                    add_param = re.compile(f'{trim_coin}usdt/|/usdt|usdt|/usd|usd/|usd')
                    coin = re.findall(add_param, trim_msg[i])
                    if coin:
                        coin = trim_msg[i].replace(ic, '').replace(coin[0], '').strip().upper()
                        logging.info(f'Deduction of coins from the message successfully: {coin}')
                        break
                else:
                    names_coins = await gel_all_coins(demo, trs)
                    for i in range(len(trim_msg)):
                        trim_substr = re.sub('[^\w]', '', trim_msg[i]).upper()
                        if trim_substr in names_coins:
                            logging.info(
                                f'The coin is found in the search process'
                                f' in a message from the temporary storage: {trim_substr}'
                            )
                            coin = trim_substr
                            break
                    else:
                        logging.warning(
                            f'The coin is not found in the search process in the message'
                            f' and it is not in the temporary storage: {trim_msg}'
                        )
                        return False
            except Exception as err:
                logging.error(err)
                return False
            try:
                logging.info('Check for availability in white and black lists')
                if coin in white_list or (coin not in white_list and coin not in black_list):
                    if white_list != ['']:
                        try:
                            white_list.index(coin)
                            logging.info(f'Found coin from the whitelist: {coin}')
                        except ValueError:
                            logging.info(f'Not found coin from the whitelist: {coin}')
                            return False
                    else:
                        logging.info(f'White list is empty')
                    try:
                        names_coins = await gel_all_coins(demo, trs)
                        if coin in names_coins:
                            logging.info(f'Coin have in temporary storage: {coin}')
                            return coin
                        else:
                            logging.warning(f'The coin has no temporary storage: {coin}')
                            return False
                    except Exception as err:
                        logging.error(err)
                elif coin in black_list:
                    logging.warning(f'Found coin from the blacklist: {coin}')
                    return False
            except Exception as err:
                logging.error(err)
    else:
        logging.warning(f'The introductory word for searching coins is not found: {intro_coin}')
        return False


async def search_STP(searchWords, message, prefix, splitter=None, trimmer=None) -> list | float:
    """Мультиобработка стоп-лоса, тейк-профита, прайса."""
    try:
        take_profit = []

        for searchWord in searchWords:
            try:
                indX = searchWord.index(')')
                searchWord = rf'{searchWord[:indX]}\{searchWord[indX:]}'
            except ValueError:
                pass

            searchWord = re.compile(searchWord)
            try:
                actually_word = searchWord.findall(message)[0]
                logging.info(f'{prefix.capitalize()} found: {actually_word}')
            except (Exception, IndexError):
                logging.warning(f'Wrong value "{prefix}" in O:: column, the default value will be 2 %')
                return False

            indexWord = message.find(actually_word)
            format_msg = message[indexWord::].split('\n')
            # Отсекает лишние символы после указанного слова
            if trimmer is not None:
                format_msg = [fm.split('%')[0] for fm in format_msg]
            try:
                for fm in range(len(format_msg)):
                    try:
                        format_msg[fm].index(actually_word)
                    except ValueError:
                        break
                    trim_value = format_msg[fm].split(actually_word)
                    trim_value = [i.strip() for i in trim_value if i != '']
                    trim_value = trim_value[0].split(splitter)
                    logging.info(f'Substring with "{prefix}" found: {trim_value}')

                    for i in trim_value:
                        try:
                            # Форматирует строку и удаляет всё кроме цифр и "."
                            value = float(re.sub('[^\d.]', '', i.replace(',', '.')))
                            round_value = round(value, 4)
                            if prefix == 'take-profit':
                                logging.info(f'The value obtained "{prefix}": {value}')
                                take_profit.append(round_value)
                            elif prefix == 'stop-loss':
                                logging.info(f'Got received value "{prefix}": {round_value}')
                                return round_value
                            elif prefix == 'price':
                                logging.info(f'Got received value "{prefix}": {round_value}')
                                return round_value
                        except (ValueError, TypeError):
                            continue
            except Exception as err:
                logging.error(err)
        else:
            logging.info(f'Got received value "{prefix}": {take_profit}')
            return take_profit
    except Exception as err:
        logging.error(err)
        return False
