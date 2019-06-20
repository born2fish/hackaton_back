from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from application.middlewares import get_translator
from application.models import UserProfile


async def get_inline_keyboard(reply_markup, callbacks):
    result_inline_keyboard = []
    for line_ind, line in enumerate(reply_markup):
        result_line = []
        for btn_ind, button_name in enumerate(line):
            btn = InlineKeyboardButton(text=str(button_name), callback_data=callbacks[line_ind][btn_ind])
            result_line.append(btn)
        result_inline_keyboard.append(result_line)
    return InlineKeyboardMarkup(inline_keyboard=result_inline_keyboard, row_width=1)


async def get_keyboard(reply_markup, one_time_keyboard=False, selective=True):
    result_keyboard = []
    for line in reply_markup:
        result_line = []
        for button_name in line:
            btn = KeyboardButton(text=str(button_name))
            result_line.append(btn)
        result_keyboard.append(result_line)
    return ReplyKeyboardMarkup(keyboard=result_keyboard, resize_keyboard=True,
                               one_time_keyboard=one_time_keyboard, selective=selective)


class KeyboardFactory:
    def __init__(self, profile: UserProfile):
        self.profile = profile
        self._ = None

    @classmethod
    async def create(cls, profile):
        self = cls(profile=profile)
        self._ = await get_translator(self.profile)
        return self

    @staticmethod
    async def get_simple(reply_markup, one_time_keyboard=False, selective=True):
        result_keyboard = []
        for line in reply_markup:
            result_line = []
            for button_name in line:
                btn = KeyboardButton(text=str(button_name))
                result_line.append(btn)
            result_keyboard.append(result_line)
        return ReplyKeyboardMarkup(keyboard=result_keyboard, resize_keyboard=True,
                                   one_time_keyboard=one_time_keyboard, selective=selective)

    @staticmethod
    async def get_inline(reply_markup, callbacks):
        await get_inline_keyboard(reply_markup=reply_markup, callbacks=callbacks)

    async def main_keyboard(self):
        reply_markup = [
            [self._('💎 Shop'), self._('🗺 Map')],
            [self._('💳 Balance'), self._('📟️ System')],
        ]
        return await self.get_simple(reply_markup=reply_markup)

    async def my_wallet_keyboard(self):
        reply_markup = [
            [self._('Add'), self._('Withdraw')],
            ['🔙'],
        ]
        return await self.get_simple(reply_markup=reply_markup)

    async def shop_keyboard(self):
        reply_markup = [
            [self._('Buy 💎'), self._('Sell 💎')],
            ['🔙'],
        ]
        return await self.get_simple(reply_markup=reply_markup)

    async def map_keyboard(self):
        deny_top_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        deny_left_list = [1, 11, 21, 31, 41, 51, 61, 71, 81, 91]
        deny_right_list = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        deny_bottom_list = [91, 92, 93, 94, 95, 96, 97, 98, 99, 100]
        deny_top = True if self.profile.position in deny_top_list else False
        deny_left = True if self.profile.position in deny_left_list else False
        deny_right = True if self.profile.position in deny_right_list else False
        deny_bottom = True if self.profile.position in deny_bottom_list else False
        cb = [[]]
        rm = [[]]

        if not deny_top:
            rm[0].append('⬆️')
            cb[0].append('TOP')
        if not deny_left:
            rm[0].append('⬅️')
            cb[0].append('LEFT')
        if not deny_right:
            rm[0].append('➡️')
            cb[0].append('RIGHT')
        if not deny_bottom:
            rm[0].append('⬇️')
            cb[0].append('BOTTOM')
        rm.append([self._('🕳 Bury'), self._('⛏ Search'), self._('🌏 World map')])
        cb.append(['bury', 'search', 'map'])
        return await get_inline_keyboard(reply_markup=rm, callbacks=cb)

    async def settings_keyboard(self):
        reply_markup = [
            [self._('Language'), self._('Mode')],
            [self._('Payout address'), '🔙']
        ]
        return await self.get_simple(reply_markup=reply_markup)

    async def system_keyboard(self):
        reply_markup = [
            [self._('🔧 Settings'), self._('🗄 Profile')],
            [self._('🏴‍☠️ Help'), '🔙']
        ]
        return await self.get_simple(reply_markup=reply_markup)

    async def cancel_keyboard(self):
        return await get_inline_keyboard(reply_markup=[[self._('Cancel')]], callbacks=[['cancel']])

    async def payment_approve_keyboard(self, btc_count):
        return await get_inline_keyboard(reply_markup=[['Подтвердить', 'Отменить']],
                                         callbacks=[['make_pay|%s_%s' % (self.profile.id, btc_count), 'cancel_pay']])

    async def back_keyboard(self):
        reply_markup = [
            [
                '🔙'
            ]
        ]
        return await self.get_simple(reply_markup=reply_markup)

    async def return_keyboard(self):
        return await get_inline_keyboard(reply_markup=[[self._('↩️ Return')]], callbacks=[['return']])

    async def yes_no_keyboard(self, payload):
        return await get_inline_keyboard(
            reply_markup=[[self._('Yes'), self._('No')]], callbacks=[['yes|%s' % payload, 'no|%s' % payload]]
        )
