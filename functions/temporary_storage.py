import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Union

from config import config


@dataclass
class TemporaryRequestStorage:
    """Временное хранилище запроса на установленное время."""
    current_time_google: Union[datetime, None] = None
    current_time_bybit: Union[datetime, None] = None
    time_called_bybit: datetime = datetime.now()
    time_called_google: datetime = datetime.now()
    names: Set = field(default_factory=set)
    lotSizeFilter: Dict = field(default_factory=dict)
    priceFilter: Dict = field(default_factory=dict)
    google_param: List = field(default_factory=list)

    def check_time_bybit(self):
        if self.set_current_time_bybit(prefix='bybit'):
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

    def check_time_google(self):
        if self.set_current_time_google(prefix='google'):
            return True
        delta = (self.current_time_google - self.time_called_google).seconds
        if delta > config.google.timeout:
            self.time_called_google = datetime.now()
            return True
        return False

    def set_current_time_google(self, prefix):
        if self.current_time_google is None:
            self.current_time_google = datetime.now()
            logging.info(f'Initialization of the current time {prefix}')
            return True
        self.current_time_google = datetime.now()
        return False

    def set_current_time_bybit(self, prefix):
        if self.current_time_bybit is None:
            self.current_time_bybit = datetime.now()
            logging.info(f'Initialization of the current time {prefix}')
            return True
        self.current_time_bybit = datetime.now()
        return False


trs = TemporaryRequestStorage()
