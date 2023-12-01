import os

import httplib2
from googleapiclient import discovery

from dotenv import load_dotenv

load_dotenv()


def google_sheet_auto_bot() -> discovery:
    """Подключение к таблице по API."""
    discoveryUrl = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
    service = discovery.build(
        'sheets',
        'v4',
        http=httplib2.Http(),
        discoveryServiceUrl=discoveryUrl,
        developerKey=os.getenv('DEVELOPER_API_KEY')
    )
    return service
