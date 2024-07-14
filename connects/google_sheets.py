import os

import httplib2
from googleapiclient import discovery

from config import config


def google_sheet_auto_bot() -> discovery:
    """Подключение к таблице по API."""
    discoveryUrl = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
    service = discovery.build(
        'sheets',
        'v4',
        http=httplib2.Http(),
        discoveryServiceUrl=discoveryUrl,
        developerKey=config.google.api_key
    )
    return service
