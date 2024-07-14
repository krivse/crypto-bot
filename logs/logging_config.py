import logging
from logging.handlers import TimedRotatingFileHandler

import colorlog


# Настройка логирования
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.WARNING)
# запись в файл
filename = logging.handlers.TimedRotatingFileHandler(
    'logs/logs/auto_bot.log',
    'midnight',  # раз в сутки
    1,          # раз в 1 день
    0       # не удалять старые файлы
)

console = logging.StreamHandler()  # вывод в консоль

formatter = colorlog.ColoredFormatter(
    '%(log_color)s[%(levelname)s][%(asctime).19s][%(filename)s %(lineno)d][%(name)s]:%(reset)s %(message)s',
    log_colors={
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red,bg_blue'
    }
)
console.setFormatter(formatter)
# Настройка логирования
logging.basicConfig(
    handlers=(filename, console),  # одновременное логирование в консоль и в файл
    level=logging.INFO
)
