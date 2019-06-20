from aiogram import Bot
from aiogram.types import Update

from application.handlers.callback_query.settings_menu import SetLanguageHandler
from application.handlers.hybrid.commands import StartHandler
from application.handlers.hybrid.events import NewChatTitleHandler, NewChatPhotoHandler
from application.handlers.hybrid.expect import ExpectBtcWalletHandler
from application.handlers.messages.main_menu import AllMessagesHandler
from application.settings import LANGUAGES
from application.support.redis_support import StateMachine

# TODO: add languages
MESSAGE_MAP = {
    # UpdateMapHandler: ['/update'],
}

CALLBACK_MAP = {
    'cancel': StartHandler,
}

# add language handler
for lang in LANGUAGES:
    CALLBACK_MAP["%s %s" % (lang['flag'], lang['name'])] = SetLanguageHandler

FSM_MAP = {
    'EXPECT_BTC_WALLET': ExpectBtcWalletHandler,
}


async def _get_message_handler(update: Update):
    user_text = update.message.text
    if user_text and '/start' in user_text:
        try:
            __, user_code = user_text.split(' ')
            handler = StartHandler
        except Exception:
            handler = StartHandler
    elif update.message.new_chat_title:
        handler = NewChatTitleHandler
    elif update.message.new_chat_photo:
        handler = NewChatPhotoHandler
    else:
        handler = AllMessagesHandler
        for h in MESSAGE_MAP:
            commands = MESSAGE_MAP[h]
            if user_text in commands:
                handler = h
    return handler


async def _get_callback_query_handler(dispatcher):
    data = dispatcher.update.callback_query.data
    payload = None
    try:
        handler_key, payload = data.split('|')
        handler = CALLBACK_MAP[handler_key](dispatcher=dispatcher)
    except (KeyError, ValueError, IndexError, AttributeError):
        try:
            handler = CALLBACK_MAP[data](dispatcher=dispatcher)
        except KeyError:
            handler = None
    return handler, payload


class Dispatcher:
    cq_data = None
    heard = None

    class Types:
        message = 'message',
        callback_query = 'callback_query'
        channel_post = 'channel_post'

    available_types = [Types.message, Types.callback_query, Types.channel_post]

    def __init__(self, incoming: dict, bot: Bot):
        self.incoming_dict = incoming
        self.bot = bot
        self.update = Update(**self.incoming_dict)

    async def check_state_machine(self, profile):
        if profile:
            sm = StateMachine(profile=profile)
            current_state = await sm.get_redis_state()
            if current_state != 'REST':
                handler = FSM_MAP[current_state](dispatcher=self)
                return handler
        return None

    async def _get_handler_type(self):
        if self.update.message:
            handler_type = self.available_types[0]
            self.heard = self.update.message.text
        elif self.update.callback_query:
            handler_type = self.available_types[1]
            self.data = self.update.callback_query.data
        else:
            handler_type = None
        return handler_type

    async def get_handler(self):

        handler_type = await self._get_handler_type()
        payload = None
        if handler_type:
            # logging.info("Handler type: {handler_type}".format(handler_type=handler_type[0]))
            if handler_type == self.available_types[0]:
                handler = await _get_message_handler(update=self.update)
            elif handler_type == self.available_types[1]:
                handler, payload = await _get_callback_query_handler(dispatcher=self)
            else:
                handler = None
        else:
            handler = None
        return handler, payload
