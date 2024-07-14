from config import config
from handlers.channel_scanner import bybit_on
from logs.logging_config import logging

from telethon import TelegramClient


async def client(**kwargs):
    try:
        _client = TelegramClient('anon', config.telegram.api_id, config.telegram.api_hash)
        logging.info('Starting bot')
        await _client.start(phone=config.telegram.phone, password=config.telegram.password)
        # С помощью свойств передаём необходимые объекты в обработчик событий
        _client.ws = kwargs.get('ws')  # экземпляр класса bybit для получения сделок по web-socket
        _client.queue = kwargs.get('queue')  # экземпляр класса queue для передачи процента стоп-лос
        _client.service = kwargs.get('service')
        _client.add_event_handler(bybit_on)  # регистрируем обработчик событий
        await _client.run_until_disconnected()
    except Exception as err:
        logging.error(err)
