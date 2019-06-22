from peewee import ProgrammingError, BooleanField
from playhouse.migrate import migrate, PostgresqlMigrator

from treasures_bot.models import database, User, UserProfile, UserFriend, Payment, Transaction, BaseDocument, Invoice
from treasures_bot.utils import print_tb
migrator = PostgresqlMigrator(database)

try:
    real_mode = BooleanField(default=False)
    migrate(migrator.add_column('bot_profile', 'real_mode', real_mode))
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()