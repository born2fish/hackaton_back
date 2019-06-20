import asyncio
import logging
import sys

import aiohttp_jinja2
import jinja2
from aiohttp import web
from application.models import database
from application.routes import setup_routes
from application.settings import MAIN_APP_NAME
from application.support.bitcoin_support import BtcRateTicker
from application.tasks import update_rates_task, clear_webhooks_task
from application.utils import get_config, create_app, ROOT_DIR


class SkipTimeouts(logging.Filter):
    def filter(self, rec):
        if (rec.levelno == logging.INFO and
                rec.msg.startswith('poll') and
                rec.msg.endswith(': timeout') and
                990 < rec.args[0] < 1000 and
                1000 < rec.args[1] < 1010):
            return False  # hide this record
        return True


async def init_pg(app):
    app['db'] = database


async def close_pg(app):
    app['db'].close()
    await app['db'].wait_closed()


def init(loop, argv):
    logging.getLogger('asyncio').addFilter(SkipTimeouts())
    #
    # define your command-line arguments here
    #
    config = get_config(argv)
    # setup application and extensions
    app = create_app(config=config)
    setup_routes(app)
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader(MAIN_APP_NAME, 'templates'))

    # create connection to the database
    app.on_startup.append(init_pg)
    # shutdown db connection on exit
    app.on_cleanup.append(close_pg)
    # setup views and routes
    # setup_middlewares(app)

    # jinja_loader = jinja2.FileSystemLoader('./templates')
    # aiohttp_jinja2.setup(app, loader=jinja_loader)
    jinja_env = aiohttp_jinja2.get_env(app)
    jinja_env.globals['STATIC'] = '/static/'
    jinja_env.globals['_'] = app['gettext']
    # Locale settings
    return app


def main(argv):
    # init logging
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()
    logging.info("ROOT_DIR = %s" % ROOT_DIR)
    # loop.set_debug(enabled=True)
    app = init(loop, argv)

    ticker = BtcRateTicker()
    rates_task = loop.create_task(update_rates_task(loop=loop, rates_ticker=ticker, app=app))
    webhook_task = loop.create_task(clear_webhooks_task(loop=loop, app=app))

    web.run_app(app, access_log=None,
                host=app['config']['app']['host'],
                port=app['config']['app']['port'])

    loop.run_until_complete(rates_task)
    loop.run_until_complete(webhook_task)


if __name__ == '__main__':
    main(sys.argv[1:])
