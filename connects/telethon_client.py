from handlers.channel_scanner import bybit_on
from logs.logging_config import logging
import os

from telethon import TelegramClient
from dotenv import load_dotenv


load_dotenv()


async def client(**kwargs):
    try:
        _client = TelegramClient('anon', int(os.getenv('API_ID')), os.getenv('API_HASH'))
        logging.info('Starting bot')
        async with _client:
            # С помощью свойств передаём необходимые объекты в обработчик событий
            _client.trs = kwargs.get('trs')  # экземпляр класса временного хранилища
            _client.ws = kwargs.get('ws')  # экземпляр класса bybit для получения сделок по web-socket
            _client.queue = kwargs.get('queue')  # экземпляр класса queue для передачи процента стоп-лос
            _client.add_event_handler(bybit_on)  # регистрируем обработчик событий
            await _client.run_until_disconnected()
    except Exception as err:
        logging.error(err)
