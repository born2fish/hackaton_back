from application.models import database, Person, Skill, PersonSkill
from application.utils import print_tb

try:
    database.create_tables(
        [
            Person, Skill, PersonSkill
        ]
    )
except Exception as e:
    print_tb(e)
    database.rollback()
