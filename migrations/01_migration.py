from peewee import ProgrammingError

from treasures_bot.models import database, User, UserProfile, UserFriend
from treasures_bot.utils import print_tb

try:
    # database.drop_table(Sector)
    database.create_tables(
        [
            User, UserProfile, UserFriend
        ]
    )
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()