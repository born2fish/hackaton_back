from peewee import ProgrammingError, ForeignKeyField, IntegerField
from playhouse.migrate import migrate, PostgresqlMigrator

from treasures_bot.models import database,  UserProfile
from treasures_bot.utils import print_tb

migrator = PostgresqlMigrator(database)

try:
    steps = IntegerField(default=5)
    migrate(migrator.add_column('bot_profile', 'steps', steps))
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()