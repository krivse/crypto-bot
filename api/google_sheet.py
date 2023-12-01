import os
from typing import List

from connects.google_sheets import google_sheet_auto_bot


def get_auto_bot() -> List:
    """Получение всех данных из гугл-таблицы."""
    service = google_sheet_auto_bot()
    result = service.spreadsheets().values().get(
        spreadsheetId=os.getenv('SHEETS_ID'),
        range="A2:X999",
        majorDimension='ROWS'
    ).execute()

    values = result.get('values', [])

    return values
