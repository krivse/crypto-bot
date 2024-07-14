import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Telegram:
    api_id: int
    api_hash: str
    phone: str
    password: str | None


@dataclass
class Bybit:
    testnet: bool
    api_key: str
    api_secret: str
    api_key_testnet: str
    api_secret_testnet: str
    timeout: int


@dataclass
class Google:
    api_key: str
    sheets_id: str
    timeout: int


@dataclass
class Config:
    telegram: Telegram
    bybit: Bybit
    google: Google


def get_config():
    return Config(
            telegram=Telegram(
                api_id=int(os.getenv('API_ID')),
                api_hash=os.getenv('API_HASH'),
                phone=os.getenv('PHONE'),
                password=os.getenv('PASSWORD'),
            ),
            bybit=Bybit(
                testnet=bool(os.getenv('TESTNET')),
                api_key=os.getenv('BYBIT_API_KEY'),
                api_secret=os.getenv('BYBIT_API_SECRET'),
                api_key_testnet=os.getenv('BYBIT_API_KEY_TESTNET'),
                api_secret_testnet=os.getenv('BYBIT_API_SECRET_TESTNET'),
                timeout=int(os.getenv('TIMEOUT_BYBIT'))
            ),
            google=Google(
                api_key=os.getenv('DEVELOPER_API_KEY'),
                sheets_id=os.getenv('SHEETS_ID'),
                timeout=int(os.getenv('TIMEOUT_GOOGLE'))
            )
        )


config = get_config()
