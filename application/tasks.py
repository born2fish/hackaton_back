import asyncio
import datetime

from aiohttp import web

from application.middlewares import get_translator
from application.models import objects, Rate, RateHistory, Webhook, Commission, User
from application.settings import WEBHOOK_LIFETIME_HOURS
from application.support.bitcoin_support import BtcRateTicker, BlockcypherWorker
from application.support.user_support import get_user_profile
from application.utils import print_tb, get_config, create_app


async def update_rates_task(loop, rates_ticker: BtcRateTicker, app: web.Application):
    btc_worker =  BlockcypherWorker(config=app['config'])
    async def update_rates_history():
        count_query = RateHistory.select()
        count = await objects.count(count_query)
        await objects.create(
            RateHistory, btc_usd=bitmex_btc_usd, coinbase=coinbase_btc_usd, kraken=kraken_btc_usd
        )
        if count >= 11:
            query = RateHistory.select().order_by(RateHistory.id.asc())
            histories = await objects.execute(query)
            try:
                for hist in histories[0: count-10]:
                    await objects.delete(hist)
            except Exception as e:
                print_tb(e)

    async def update_btc_commission():
        low_fee_per_kb, medium_fee_per_kb, high_fee_per_kb = await btc_worker.get_current_transaction_fees()
        commission, created = await objects.get_or_create(
            Commission,
            low_fee_per_kb=low_fee_per_kb, medium_fee_per_kb=medium_fee_per_kb, high_fee_per_kb=high_fee_per_kb
        )
        print('Commission was updated: %s' % commission)

    bot = app['bot']
    print("Bot %s is ready to serve in rates task" % bot)
    while True:
        bitmex_btc_usd, coinbase_btc_usd, kraken_btc_usd = await rates_ticker.get_btc_usd_rates()
        rate, created = await objects.get_or_create(Rate)
        rate.btc_usd = bitmex_btc_usd
        rate.coinbase = coinbase_btc_usd
        rate.kraken = kraken_btc_usd
        await objects.update(rate)
        print("BTC/USD Rates: bitmex: %s | coinbase: %s | kraken: %s" % (rate.btc_usd, rate.coinbase, kraken_btc_usd))
        await update_rates_history()
        await update_btc_commission()
        await asyncio.sleep(600, loop=loop)


async def clear_webhooks_task(loop, app: web.Application):
    # todo: think about private message to user about this
    btc_worker = BlockcypherWorker(config=app['config'])
    bot = app['bot']
    print("Bot %s is ready to serve in webhooks task" % bot)
    while True:
        all_hooks = await objects.execute(Webhook.select())
        print('Total webhooks: %s' % len(all_hooks))
        for wh in all_hooks:
            if datetime.datetime.now() - wh.updated_at >= datetime.timedelta(hours=WEBHOOK_LIFETIME_HOURS):
                await btc_worker.unsubscribe_webhook(webhook_id=wh.webhook_id)
                await objects.delete(wh)
        await asyncio.sleep(300, loop=loop)


async def global_scheduler(argv):
    config = get_config(argv=[])
    app = create_app(config=config)
    bot = app['bot']
    all_users = await objects.execute(query=User.select())
    for user in all_users:
        try:
            await objects.update(user)
            profile = await get_user_profile(user=user)
            _ = await get_translator(profile)
            profile.steps += 2
            await objects.update(profile)
            message_text = "%s <i>%s</i> %s: <b>+2</b> 🥾" % (_('You have been '), _('recovered'), _('a bit and can move on'))
            print("%s\n" % user)
            await bot.send_message(chat_id=user.id, text=message_text, parse_mode="HTML")
        except Exception as e:
            print_tb(e)