from peewee import ProgrammingError, ForeignKeyField, IntegerField
from playhouse.migrate import migrate, PostgresqlMigrator

from treasures_bot.models import database,  UserProfile
from treasures_bot.utils import print_tb

migrator = PostgresqlMigrator(database)

try:
    profile_id = IntegerField(default=0)
    migrate(migrator.add_column('bot_webhook', 'profile_id', profile_id))
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()