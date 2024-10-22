import logging
from dataclasses import dataclass, field
from datetime import datetime

from config import config


@dataclass
class TemporaryRequestStorage:
    """Временное хранилище запроса на установленное время."""
    current_time_google: datetime | None = None
    current_time_bybit: datetime | None = None
    time_called_bybit: datetime = datetime.now()
    time_called_google: datetime = datetime.now()
    names: set = field(default_factory=set)
    lotSizeFilter: dict = field(default_factory=dict)
    priceFilter: dict = field(default_factory=dict)
    google_param: list = field(default_factory=list)

    def check_time(self, prefix: str) -> bool:
        if prefix == 'google':
            if self.set_current_time(prefix='google'):
                return True
            delta = (self.current_time_google - self.time_called_google).seconds
            if delta > config.google.timeout:
                self.time_called_google = datetime.now()
                return True
            return False
        else:
            if self.set_current_time(prefix='bybit'):
                return True
            delta = (self.current_time_bybit - self.time_called_bybit).seconds

            if delta > config.bybit.timeout:
                self.time_called_bybit = datetime.now()
                return True
            hour = (config.bybit.timeout - delta) / 3600 - 1
            minute = 0 if 60 * (hour % 1) - 1 == -1 else 60 * (hour % 1) - 1
            logging.info(f'Time until the next request for updating list of coins: '
                         f'{"%.0f" % hour} hour {minute:02.0f} minute')
            return False

    def set_current_time(self, prefix: str) -> bool:
        if prefix == 'google':
            if self.current_time_google is None:
                self.current_time_google = datetime.now()
                logging.info(f'Initialization of the current time {prefix}')
                return True
            self.current_time_google = datetime.now()
            return False
        else:
            if self.current_time_bybit is None:
                self.current_time_bybit = datetime.now()
                logging.info(f'Initialization of the current time {prefix}')
                return True
            self.current_time_bybit = datetime.now()
            return False


trs = TemporaryRequestStorage()
