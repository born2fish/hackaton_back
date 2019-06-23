from peewee import ProgrammingError, BooleanField
from playhouse.migrate import migrate, PostgresqlMigrator

from application.models import database
from application.utils import print_tb

migrator = PostgresqlMigrator(database)

try:
    sex = BooleanField(default=True)
    migrate(migrator.add_column('bot_person', 'sex', sex))
except ProgrammingError as pe:
    print_tb(pe)
    database.rollback()
except Exception as e:
    database.rollback()