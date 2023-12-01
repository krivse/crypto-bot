import logging
from datetime import date


filename = logging.FileHandler(f'logs/logs/{date.today()}_auto_bot.log')  # запись в файл
console = logging.StreamHandler()  # вывод в консоль

# Настройка логирования
logging.basicConfig(
    handlers=(filename, console),  # одновременное логирование в консоль и в файл
    level=logging.INFO,
    format='[%(levelname) 5s/%(asctime)s %(filename)s %(lineno)d] %(name)s: %(message)s',
)
