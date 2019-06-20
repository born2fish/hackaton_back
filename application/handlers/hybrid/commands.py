from application.decorators import set_state
from application.handlers.abstract_handler import AbstractHandler
from application.middlewares import get_translator
from application.models import objects
from application.settings import BLOCKED_USERS_ID_LIST
from application.support.bitcoin_support import get_usd_from_btc
from application.support.user_support import get_user, get_user_profile, \
    get_user_friend_or_none, get_or_create_user_friend
from application.utils import render_template


class StartHandler(AbstractHandler):
    async def _process_user_friend(self):
        try:
            __, user_code = self.update.message.text.split(' ')
            sponsor_user_id = await self.profile.user.get_user_id(code=user_code)
            sponsor_user = await get_user(user_id=sponsor_user_id)
            sponsor_profile = await get_user_profile(user=sponsor_user)
            reverse_user_friend = await get_user_friend_or_none(sponsor=self.profile, partner=sponsor_profile)
            if not reverse_user_friend:  # protect reverse subscription
                if sponsor_profile.id != self.profile.id:  # protect self subscription
                    if sponsor_profile.user.id not in BLOCKED_USERS_ID_LIST:
                        user_friend, created = await get_or_create_user_friend(sponsor=sponsor_profile,
                                                                               partner=self.profile)
                        if created:  # protect double subscription
                            self.profile.user.sponsor_user_id = sponsor_user_id
                            sponsor_profile.steps += 1
                            await objects.update(self.profile.user)
                            await objects.update(sponsor_profile)
                            if not sponsor_profile.real_mode:
                                translator = await get_translator(sponsor_profile)
                                message = translator(
                                    'Some user follow your referral link. You get +1 🥾 step, congratulations!')
                                await self.bot.send_message(chat_id=sponsor_user.id, text=message)
                                self.text = translator(
                                    'It will become your partner after setting up payout address in settings')
                                await self.bot.send_message(chat_id=sponsor_user.id, text=self.text)

                        else:
                            pass
                    else:
                        pass
                else:
                    pass
            else:
                pass
        except ValueError:
            pass
        except AttributeError:
            # after change language we have this error when access update.message attribute
            pass

    @set_state(state_name='REST')
    async def process_update(self):
        self.rm = await self.kf.main_keyboard()
        await self._process_user_friend()
        usd = await get_usd_from_btc(btc=self.profile.balance)
        self.text = await render_template(
            template='start',
            context={
                'profile': self.profile, 'usd': usd,
            }
        )
        await self.answer(text=self.text)
        await self.answer_cq()
