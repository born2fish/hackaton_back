from aiogram.types import ReplyKeyboardRemove

from application.decorators import set_state
from application.handlers.abstract_handler import AbstractHandler
from application.keyboards.settings import KeyboardFactory


class PaymentAddressHandler(AbstractHandler):
    @set_state(state_name='EXPECT_BTC_WALLET')
    async def process_update(self):
        self.text = self._('Please send me bitcoin address for withdrawals')
        self.rm=ReplyKeyboardRemove()
        await self.answer()


class ModeHandler(AbstractHandler):
    async def process_update(self):
        self.text = self._('Please select mode')
        factory = await KeyboardFactory(self.profile).create(self.profile)
        self.rm = await factory.select_mode_keyboard()
        await self.answer()


class LanguageHandler(AbstractHandler):
    async def process_update(self):
        self.text = self._('Please select language')
        self.rm = await KeyboardFactory.select_language_keyboard()
        await self.answer()