from application.handlers.abstract_handler import AbstractHandler
from application.handlers.hybrid.commands import StartHandler
from application.handlers.messages.main_menu import SettingsHandler
from application.middlewares import get_translator
from application.models import objects, UserFriend, User
from application.support.bitcoin_support import Billing, BlockcypherWorker
from application.support.user_support import get_root_user, get_user, get_user_profile, \
    get_user_friends_count


class ExpectBtcWalletHandler(AbstractHandler):
    award_steps = 10

    async def activate_user_friend(self, old_address):
        if not old_address:
            sponsor = await get_user(user_id=self.profile.user.sponsor_user_id)
            sponsor_profile = await get_user_profile(user=sponsor)
            sponsor_profile.steps += self.award_steps
            await objects.update(sponsor_profile)
            user_friend = await objects.get(UserFriend, sponsor=sponsor_profile, partner=self.profile)
            user_friend.active = True
            print(user_friend)
            await objects.update(user_friend)
            translator = await get_translator(sponsor_profile)
            await self.bot.send_message(
                chat_id=sponsor.id, text=translator('🌈 You have new active partner, congratulations!')
            )
            await self.bot.send_message(
                parse_mode='HTML', chat_id=sponsor.id,
                text="+ <b>%s</b> 🥾 <i>%s</i>" % (self.award_steps, self._('steps'))
            )
            refs_count = await get_user_friends_count(profile=sponsor_profile)
            if refs_count % 10 == 0:
                sponsor_profile.gems += 1
                await objects.update(sponsor_profile)
                await self.bot.send_message(
                    parse_mode='HTML', chat_id=sponsor.id, text="+ <b>%s</b> <i>%s</i>" % (1, '💎')
                )
                root = await get_root_user()
                await self.bot.send_message(
                    parse_mode='HTML', chat_id=root.id, text="User %s get +1💎 (refs_count=%s)" % (sponsor, refs_count)
                )

    async def process_update(self):
        try:
            user_input_data = self.update.message.text
            balance = await Billing.get_balance(
                wallet_address=user_input_data, coin_symbol=BlockcypherWorker(self.config).coin_symbol
            )
            int(balance)
            old_address = self.profile.btc_payout_address
            self.profile.btc_payout_address = user_input_data
            await objects.update(self.profile)
            self.text = self._('☑️ Payout address was updated!')
            try:
                await self.activate_user_friend(old_address=old_address)
            except User.DoesNotExist:
                pass
            await self.sm.set_redis_state(state='REST')
            redirect_handler = await SettingsHandler(dispatcher=self.dp).create(self.dp)
            await redirect_handler.process_update()
        except AttributeError:
            await self.sm.set_redis_state(state='REST')
            self.text = self._('🌬 Оk, forget about this.')
            await self.re_answer()
            redirect_handler = await StartHandler(dispatcher=self.dp).create(self.dp)
            await redirect_handler.process_update()
        except TypeError:
            self.rm = await self.kf.cancel_keyboard()
            self.text = self._('🚫 This address is not suite me. Please try another one.')
            await self.answer()
        await self.sm.set_back_handler(handler_name='StartHandler')
