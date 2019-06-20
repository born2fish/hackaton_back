from application.handlers.abstract_handler import AbstractHandler


class NewChatTitleHandler(AbstractHandler):

    async def process_update(self):
        chat_id = self.update.message.chat.id
        txt = await self.brain.response_randomizer([
            'Oh, i like new title',
            'Nice fresh title, friends. That is cool',
            'New title. With love 💝!',
        ])
        self.text = txt
        await self.bot.send_message(chat_id=chat_id, text=self.text)


class NewChatPhotoHandler(AbstractHandler):

    async def process_update(self):
        chat_id = self.update.message.chat.id
        txt = await self.brain.response_randomizer([
            'Oh, i like new photo',
            'Nice photo for our community, friends. That is cool',
            'So nice photo 💝!',
        ])
        self.text = txt
        await self.bot.send_message(chat_id=chat_id, text=self.text)