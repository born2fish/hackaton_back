from peewee import ProgrammingError

from treasures_bot.models import database, User, UserProfile, UserFriend, Payment, Transaction, BaseDocument, Invoice
from treasures_bot.utils import print_tb

try:
    # database.drop_table(Sector)
    database.create_tables(
        [
            Transaction, BaseDocument, Invoice, Payment
        ]
    )
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()