from pybit.exceptions import FailedRequestError

from config import config
from logs.logging_config import logging

from pybit.unified_trading import HTTP


def session(demo) -> HTTP:

    api_key = config.bybit.api_key
    api_secret = config.bybit.api_secret
    if demo:
        api_key = config.bybit.api_key_demo
        api_secret = config.bybit.api_secret_demo
    try:
        instance_session = HTTP(
            api_key=api_key,
            api_secret=api_secret,
            demo=demo
        )
        logging.info('Request for Bybit')
        return instance_session
    except FailedRequestError as err:
        logging.error(repr(err))
