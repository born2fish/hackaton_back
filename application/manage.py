import importlib

import os

from application.utils import print_tb


def migrate():
    # create tables migration:
    migrations_pack = 'migrations'
    # importlib.import_module('%s.create_tables' % migrations_pack)

    # other migrations:
    all_modules = os.listdir(os.path.join(os.path.dirname(__file__).replace('application', ''), 'migrations'))
    for mdl in sorted(all_modules):
        if 'migration' in mdl:
            print(mdl)
            try:
                importlib.import_module('%s.%s' % (migrations_pack, mdl.replace('.py', '')))
            except Exception as e:
                print_tb(e)
        else:
            pass

