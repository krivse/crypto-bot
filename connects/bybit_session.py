from pybit.exceptions import FailedRequestError

from config import config
from logs.logging_config import logging

from pybit.unified_trading import HTTP


def session(testnet) -> HTTP:

    api_key = config.bybit.api_key
    api_secret = config.bybit.api_secret
    if testnet:
        api_key = config.bybit.api_key_testnet
        api_secret = config.bybit.api_secret_testnet
    try:
        instance_session = HTTP(
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet
        )
        logging.info('Request for Bybit')
        return instance_session
    except FailedRequestError as err:
        logging.error(repr(err))
