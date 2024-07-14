import logging
from typing import List

from googleapiclient import discovery
from googleapiclient.errors import HttpError

from config import config


def get_auto_bot(service: discovery) -> List:
    """Получение всех данных из гугл-таблицы."""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=config.google.sheets_id,
            range="A2:Z999",
            majorDimension='ROWS'
        ).execute()

        values = result.get('values', [])
        return values
    except HttpError as e:
        logging.error(f"An error occurred: {e}")
