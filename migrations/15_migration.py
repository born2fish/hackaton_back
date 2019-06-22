from peewee import ProgrammingError, ForeignKeyField, IntegerField, BooleanField
from playhouse.migrate import migrate, PostgresqlMigrator

from treasures_bot.models import database,  UserProfile
from treasures_bot.utils import print_tb

migrator = PostgresqlMigrator(database)

try:
    active = BooleanField(default=False)
    migrate(migrator.add_column('user_friend', 'active', active))
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()