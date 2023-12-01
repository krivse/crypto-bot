import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Set


@dataclass
class TemporaryRequestStorage:
    """Временное хранилище запроса на 24 часа."""
    time_response: [datetime, None] = None
    time_called: datetime = datetime.now()
    names: Set = field(default_factory=set)
    lotSizeFilter: Dict = field(default_factory=dict)
    priceFilter: Dict = field(default_factory=dict)

    def check_time(self):
        delta = (self.time_called - self.time_response).seconds
        if delta > 86400:
            return True
        hour = delta / 60 / 60 - 1
        minute = 60 * (hour % 1) - 1
        logging.info(f'Time until the next request: {"%.0f" % hour} hour {"%.0f" % minute} minute')
        return False
