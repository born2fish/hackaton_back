import datetime

from application.handlers.abstract_handler import AbstractHandler
from application.models import objects, UserProfile, Treasure
from application.settings import GEM_PRICE, START_DATE
from application.support.bitcoin_support import get_usd_from_btc, BlockcypherWorker
from application.support.user_support import get_guests_count, get_user_friends_count, get_user_friends_count_today
from application.utils import render_template, get_flag, get_btc_from_satoshis, get_satoshis_commission


class AllMessagesHandler(AbstractHandler):
    async def process_update(self):
        self.text = self._('Sorry but i can not understand this command')
        await self.answer()


class BackHandler(AbstractHandler):
    async def process_update(self):
        from application.handlers.hybrid.commands import StartHandler
        assert StartHandler
        handler_name = await self.sm.get_back_handler()
        if not handler_name:
            handler_name = 'StartHandler'
        try:
            handler = locals()[handler_name]
        except KeyError:
            handler = globals()[handler_name]
        instance = handler(dispatcher=self.dp)
        result_handler = await instance.create(self.dp)
        await result_handler.process_update()


class SystemHandler(AbstractHandler):
    async def _count_gems(self, gems):
        gems_count = 0
        for g in gems:
            gems_count += g.amount
        return gems_count

    async def process_update(self):
        self.rm = await self.kf.system_keyboard()
        self.text = self._('System settings and main information')
        await self.sm.set_back_handler(handler_name='StartHandler')
        await self.answer(disable_web_page_preview=True)
        gems_count = await self._count_gems(await objects.execute(Treasure.select().where(Treasure.is_real == True)))
        demo_gems_count = await self._count_gems(
            await objects.execute(Treasure.select().where(Treasure.is_real == False)))
        self.text = await render_template(
            template='statistics',
            context={
                'profile': self.profile,
                'total_players': await objects.count(UserProfile.select()),
                'active_players': await objects.count(
                    UserProfile.select().where(UserProfile.btc_payout_address.is_null(False))
                ),
                'online_players': await objects.count(
                    UserProfile.select().where(
                        UserProfile.last_click_date >= datetime.datetime.now() - datetime.timedelta(minutes=5)
                    )
                ),
                'days_online': (datetime.datetime.now() - START_DATE).days,
                'gems': gems_count,
                'gems_demo': demo_gems_count,
            }
        )
        await self.bot.send_message(chat_id=self.profile.user.id, text=self.text, parse_mode='HTML')


class SettingsHandler(AbstractHandler):
    async def process_update(self):
        self.rm = await self.kf.settings_keyboard()
        mode = self._('REAL') if self.profile.real_mode else self._('DEMO')
        self.text = await render_template(
            template='settings', context={
                'profile': self.profile,
                'flag': await get_flag(self.profile.lang),
                'mode': mode
            }
        )
        await self.sm.set_back_handler(handler_name='SystemHandler')
        await self.answer(disable_web_page_preview=True)


class ProfileHandler(AbstractHandler):
    async def process_update(self):
        ref_link = "{production_server_host}/join/{user_code}/".format(
            production_server_host=self.config['app']['production_root_uri'],
            user_code=await self.profile.user.user_code
        )
        self.text = await render_template(
            template='profile', context={
                'profile': self.profile,
                'guests': await get_guests_count(self.profile),
                'friends': await get_user_friends_count(self.profile),
                'friends_today': await get_user_friends_count_today(self.profile),
                'ref_link': ref_link
            }
        )
        await self.answer(disable_web_page_preview=True)


class HelpHandler(AbstractHandler):
    async def process_update(self):
        await self.bot.send_message(chat_id=self.profile.user.id,
                                    text='🗯: https://t.me/TreasuresChat\n📢: https://t.me/TreasuresNews',
                                    disable_web_page_preview=True)
        self.text = await render_template(template='help', context={'profile': self.profile})
        await self.bot.send_message(chat_id=self.profile.user.id, text=self.text, parse_mode='HTML')


class MyWalletHandler(AbstractHandler):
    async def process_update(self):
        self.text = await render_template(
            template='balance',
            context={'profile': self.profile, 'usd': await get_usd_from_btc(btc=self.profile.balance)}
        )
        self.rm = await self.kf.my_wallet_keyboard()
        await self.sm.set_back_handler(handler_name='StartHandler')
        await self.answer()


class ShopHandler(AbstractHandler):
    async def process_update(self):
        fee = await get_satoshis_commission(blockcypher_worker=BlockcypherWorker(config=self.config))
        self.text = await render_template(
            template='gems',
            context={
                'profile': self.profile, 'gem_price': GEM_PRICE,
                'usd': await get_usd_from_btc(btc=GEM_PRICE),
                'fees': await get_btc_from_satoshis(satoshis_count=fee)
            }
        )
        self.rm = await self.kf.shop_keyboard()
        await self.sm.set_back_handler(handler_name='StartHandler')
        await self.answer()
