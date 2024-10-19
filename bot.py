import asyncio
import multiprocessing as mp

from connects.bybit_websocket import BybitWebSocket
from connects.google_sheets import google_sheet_auto_bot

from logs.logging_config import logging

from connects.telethon_client import client
from dotenv import load_dotenv


load_dotenv()


async def create_process(ws, queue):
    # отдельный процесс для запуска Websocket
    process = mp.Process(target=ws.execution_stream, args=(queue,))  # в реальном режиме
    process.start()  # запуск процесса


async def main():
    queue = mp.Queue()  # для передачи объектов между объектом BybitWebSocker и обработчиком событий

    ws = BybitWebSocket()  # экземпляр bybit web-socket в тестовом режиме
    # await create_process(ws, queue)
    # ws_test = BybitWebSocket(demo=True)  # экземпляр bybit web-socket в реальном режиме
    # await create_process(ws_test, queue)  # запуск процесса
    service = google_sheet_auto_bot()
    # запускаем цикл событий для обработки событий / передаём объекты в качестве контекста
    await client(ws=ws, queue=queue, service=service)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error('Bot stopped')
