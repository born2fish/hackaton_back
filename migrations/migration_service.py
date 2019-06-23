from playhouse.migrate import PostgresqlMigrator

from application.models import database

database.set_allow_sync(True)

# database.connect()
migrator = PostgresqlMigrator(database)