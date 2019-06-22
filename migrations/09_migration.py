from peewee import ProgrammingError, ForeignKeyField, IntegerField
from playhouse.migrate import migrate, PostgresqlMigrator

from treasures_bot.models import database,  UserProfile
from treasures_bot.utils import print_tb

migrator = PostgresqlMigrator(database)

try:
    sponsor_user_id = IntegerField(null=True, default=None)
    migrate(migrator.add_column('bot_user', 'sponsor_user_id', sponsor_user_id))
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()