import datetime
import logging

from application.keyboards.general import KeyboardFactory
from application.middlewares import get_translator
from application.models import objects
from application.settings import ROOT_DIR, MAIN_APP_NAME
from application.support.bitcoin_support import Billing
from application.support.redis_support import StateMachine
from application.support.user_support import get_or_create_user, get_user_profile
from application.utils import get_all_python_files, print_tb, get_config


class AbstractHandler:
    brain = None# empty here yet (add randomizer here)
    text = ''   # text for answer
    rm = None   # reply_markup for answer
    profile = None
    payload = None
    model_id = None
    _ = None    # Translator
    kf = None   # keyboard factory
    config = None
    sm = None  # state machine

    def __init__(self, dispatcher):
        self.dp = dispatcher
        self.update = dispatcher.update
        self.bot = dispatcher.bot
        self.brain = None

    @classmethod
    async def create(cls, dispatcher):
        self = cls(dispatcher=dispatcher)
        self.update = dispatcher.update
        self.bot = dispatcher.bot
        config = get_config(None)
        self.user = await get_or_create_user(self.update, self.bot, Billing(config=config))
        if self.user:
            self.profile = await get_user_profile(user=self.user)
        if self.profile:
            translator = await get_translator(self.profile)
            self._ = translator
            self.kf = await KeyboardFactory(profile=self.profile).create(profile=self.profile)
            self.sm = StateMachine(profile=self.profile)
        try:
            # wallet = await Billing(config=get_config(None)).generate_new_wallet(user=self.profile.user)
            # self.profile.btc_local_address = wallet.to_address()
            self.profile.last_click_date = datetime.datetime.now()
            await objects.update(self.profile)
        except Exception as e:
            print(e)
        return self

    async def _get_obj(self):
        cq_data = self.update.callback_query.data
        model_name = cq_data.split(':')[1].split('|')[0]
        klass = None
        uri = '%s/models/' % ROOT_DIR
        for mod_file in get_all_python_files(uri):
            mod_name = mod_file.rsplit('/', 1)[1].replace('.py', '')
            flag = True
            while flag:
                try:
                    mod = __import__('%s.models.%s' % (MAIN_APP_NAME, mod_name), fromlist=[model_name])
                    flag = False
                    klass = getattr(mod, model_name)
                except AttributeError:
                    pass
        try:
            instance = klass.get(klass.id == self.model_id)
            return instance
        except klass.DoesNotExist as kde:
            print_tb(kde)
            return None

    async def get_current_obj(self):
        obj = await self._get_obj()
        return obj

    async def channel(self, text, reply_markup, channel_model):
        logging.info("SEND message to channel: {channel}".format(channel=channel_model))
        await self.bot.send_message(text=str(text), chat_id=channel_model.channel_id, reply_markup=reply_markup,
                                    parse_mode="HTML")

    async def say(self, text, reply_markup):
        await self.bot.send_message(text=str(text), chat_id=self.profile.user.id, reply_markup=reply_markup,
                                    parse_mode="HTML")

    async def delete_old(self):
        try:
            await self.bot.delete_message(message_id=self.update.callback_query.message.message_id,
                                          chat_id=self.profile.user.id)
        except AttributeError:
            # catch redirect
            pass

    async def answer(self, disable_web_page_preview=False, text=None):
        if type(self.text) is list:
            self.text = await self.brain.response_randomizer(sources=self.text)
        if text:
            self.text = text
        await self.bot.send_message(chat_id=self.profile.user.id, text=str(self.text), reply_markup=self.rm,
                                    parse_mode='HTML', disable_web_page_preview=disable_web_page_preview)

    async def re_answer(self):
        try:
            if type(self.text) is list:
                self.text = await self.brain.response_randomizer(sources=self.text)
            await self.bot.edit_message_text(chat_id=self.profile.user.id,
                                             message_id=self.update.callback_query.message.message_id,
                                             text=str(self.text),
                                             reply_markup=self.rm,
                                             parse_mode='HTML')
        except AttributeError:
            # print_tb(err)
            await self.answer()

    async def answer_cq(self, text=None, show_alert=False):
        try:
            await self.bot.answer_callback_query(
                callback_query_id=self.update.callback_query.id,
                text=text, show_alert=show_alert
            )
        except AttributeError:
            pass
    async def process_update(self):
        await self.answer()