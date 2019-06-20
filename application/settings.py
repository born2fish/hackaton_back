import decimal
import os
import datetime

START_DATE = datetime.datetime(2019, 5, 18)
MAIN_APP_NAME = 'application'

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

ADMIN_IDS = [263948818]
BLOCKED_USERS_ID_LIST = [362993991, 75168775, 743351507]

LANGUAGES = [
    {'name': 'Русский', 'flag': '🇷🇺', 'code': 'ru', 'full_code': 'ru_RU'},
    {'name': 'English', 'flag': '🇬🇧', 'code': 'en', 'full_code': 'en_US'},
    {'name': 'Polski', 'flag': '🇵🇱', 'code': 'pl', 'full_code': 'pl_PL'},
    {'name': 'हिन्दी', 'flag': '🇮🇳', 'code': 'hi', 'full_code': 'hi_IN'},
    {'name': 'Indonesia', 'flag': '🇮🇩', 'code': 'id', 'full_code': 'id_ID'}
]

REFERRAL_CODE_MAP = {
    '0': 'q',
    '1': 'S',
    '2': 'x',
    '3': 'W',
    '4': 'd',
    '5': 'C',
    '6': 'e',
    '7': 'F',
    '8': 'v',
    '9': '0',
}

WEBHOOK_LIFETIME_HOURS = 4
MIN_WITHDRAW_AMOUNT = round(decimal.Decimal('0.003'), 5)
GEM_PRICE = round(decimal.Decimal('0.0001'), 5)
