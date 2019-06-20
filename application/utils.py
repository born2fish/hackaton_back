import argparse
import decimal
import gettext
import logging
import os
import traceback

import jinja2
import trafaret as T
from aiogram import Bot
from aiohttp import web
from babel.support import Translations
from trafaret_config import commandline

from application import settings
from application.middlewares import bot_middleware

SATOSHIS_IN_BTC = 100000000

TRAFARET = T.Dict({
    T.Key('postgres'):
        T.Dict({
            'database': T.String(),
            'user': T.String(),
            'password': T.String(),
            'host': T.String(),
            'port': T.Int(),
            'minsize': T.Int(),
            'maxsize': T.Int(),
        }),
    T.Key('app'):
        T.Dict({
            'host': T.IP,
            'port': T.Int(),
            'app_name': T.String(),
            'token': T.String(),
            'kernel_secret_param': T.String(),
            'production_root_uri': T.String(),
        }),
})


def print_tb(err):
    """ :param err is exception """
    print(err.__class__.__name__)
    logging.error("\n{err}".format(err=err))
    traceback.print_tb(err.__traceback__)


def get_all_python_files(directory):
    result = []
    for root, directories, filenames in os.walk(directory):
        for filename in filenames:
            if str(filename).endswith('.py') and not str(filename).startswith('__'):
                result.append(os.path.join(root, filename))
    return result


async def render_template(template, **context):
    # RENDERING jinja2 template without request
    # return aiohttp_jinja2.render_template('{template}.jinja2', context=context, request=request)
    try:
        file_name = '%s.jinja2' % template
        template_loc = '{root_dir}/templates/'.format(root_dir=settings.ROOT_DIR)
        print("Templates dir: %s" % template_loc)
        profile = context['context']['profile']
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_loc), extensions=['jinja2.ext.i18n']
        )
        # translations = Translations.load(dirname='app/locale', locales=[get_current_locale()], domain='loto')
        locale_path = '{root_dir}locale/'.format(root_dir=settings.ROOT_DIR.replace(settings.MAIN_APP_NAME, ''))
        print("Locales dir: %s" % locale_path)
        current_profile_locale_full_code = await get_language_full_code(code=profile.lang)
        translations = Translations.load(
            dirname=locale_path, locales=[current_profile_locale_full_code], domain='messages'
        )
        env.install_gettext_translations(translations)
        return env.get_template(file_name).render(context)
    except Exception as e:
        print_tb(e)
        return "no translation"


async def get_language_full_code(code: str) -> str:
    full_code = 'en_US'
    for l in settings.LANGUAGES:
        if l['code'] == code:
            full_code = l['full_code']
    return full_code


async def get_flag(code: str) -> str:
    flag = '🇬🇧'
    for l in settings.LANGUAGES:
        if l['code'] == code:
            flag = l['flag']
    return flag


async def get_btc_from_satoshis(satoshis_count: int) -> decimal.Decimal:
    return round(decimal.Decimal(str(satoshis_count/SATOSHIS_IN_BTC)), 5)


async def get_satoshis_from_btc(btc_count: decimal.Decimal) -> int:
    return int(btc_count*SATOSHIS_IN_BTC)


async def get_satoshis_commission(blockcypher_worker) -> int:
    __, __, high_fee_per_kb = await blockcypher_worker.get_current_transaction_fees()
    satoshis = round(high_fee_per_kb / 4, 7)
    return int(satoshis) + 2000


def get_config(argv):
    ap = argparse.ArgumentParser()
    config_path = '{root_dir}/config/application.yaml'.format(root_dir=ROOT_DIR)
    commandline.standard_argparse_options(ap,
                                          default_config=config_path)
    options = ap.parse_args(argv)
    config = commandline.config_from_options(options, TRAFARET)
    return config


def create_app(config):
    locales_path = '{root_dir}locale'.format(root_dir=ROOT_DIR)
    print(locales_path)
    gettext.bindtextdomain('messages', locales_path)
    gettext.textdomain('messages')

    # setup application and extensions
    app = web.Application(middlewares=[bot_middleware])
    # init logging and attach access_log
    # handler = app.make_handler(access_log=access_logger, access_log_format='%r %s %b')

    # load config from yaml file in current dir
    app['gettext'] = gettext.gettext
    app['config'] = config
    bot = Bot(token=config['app']['token'])
    app['bot'] = bot
    return app


ROOT_DIR = settings.ROOT_DIR.replace(settings.MAIN_APP_NAME, '')