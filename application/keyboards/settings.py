from application.keyboards.general import get_inline_keyboard
from application.middlewares import get_translator
from application.models import UserProfile
from application.settings import LANGUAGES


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
    async def select_language_keyboard():
        rm = []
        cb = []
        for language in LANGUAGES:
            language_button = '%s %s' % (language['flag'], language['name'])
            rm.append([language_button])
            cb.append([language_button])
        return await get_inline_keyboard(reply_markup=rm, callbacks=cb)

    async def select_mode_keyboard(self):
        rm = [["✔️ %s" % self._('Real')], [self._('Demo')]] if self.profile.real_mode else [[self._('Real')],
                                                                                            ["✔️ %s" % self._('Demo')]]
        cb = [['switch_mode|real'], ['switch_mode|demo']]
        return await get_inline_keyboard(reply_markup=rm, callbacks=cb)
