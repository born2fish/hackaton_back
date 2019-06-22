from playhouse.migrate import PostgresqlMigrator

from treasures_bot.models import database

database.set_allow_sync(True)

# database.connect()
migrator = PostgresqlMigrator(database)