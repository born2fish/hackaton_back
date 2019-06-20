from typing import Union

from application.handlers.abstract_handler import AbstractHandler
from application.handlers.hybrid.commands import StartHandler
from application.models import objects
from application.settings import LANGUAGES


class SetLanguageHandler(AbstractHandler):
    async def get_language_or_none(self) -> Union[dict, None]:
        flag, selected_language = self.update.callback_query.data.split(' ')
        lang = None
        for l in LANGUAGES:
            if l['flag'] == flag:
                lang = l
        return lang

    async def process_update(self):
        language= await self.get_language_or_none()
        self.profile.lang =language['code']
        self.profile.save()
        print(self.profile.lang)
        redirect_handler = await StartHandler(dispatcher=self.dp).create(self.dp)
        print(redirect_handler)
        await redirect_handler.process_update()
        await self.delete_old()


class SwitchModeHandler(AbstractHandler):
    async def process_update(self):
        mode = self.payload
        if mode == 'real':
            self.profile.real_mode = True
            await objects.update(self.profile)
        else:
            self.profile.real_mode = False
            await objects.update(self.profile)
        try:
            await self.answer_cq(text=self._('Mode was switched'))
        except:
            pass
        await self.delete_old()
        redirect_handler = await StartHandler(dispatcher=self.dp).create(self.dp)
        await redirect_handler.process_update()