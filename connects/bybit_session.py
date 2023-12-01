from logs.logging_config import logging
import os

from pybit.unified_trading import HTTP

from dotenv import load_dotenv

load_dotenv()


def session(testnet) -> HTTP:

    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    test_net = os.getenv('TESTNET')
    if testnet:
        api_key = os.getenv('BYBIT_API_KEY_TESTNET')
        api_secret = os.getenv('BYBIT_API_SECRET_TESTNET')
        test_net = testnet

    try:
        instance_session = HTTP(
            api_key=api_key,
            api_secret=api_secret,
            testnet=test_net
        )
        logging.info('Connect to Bybit')

        return instance_session
    except Exception as err:
        logging.error(err)
