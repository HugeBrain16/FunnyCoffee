import random
from cmdtools.ext.command import Command, CommandWrapper

from lib import zerochan
from lib import rule34

group = CommandWrapper()

PREFIX = "m!"


@group.command()
class Zerochan(Command):
    __aliases__ = [
        "zchan",
    ]

    def __init__(self):
        super().__init__(name="zerochan")

    @property
    def help(self):
        return "Get a random anime picture."

    async def zerochan(self):
        img = zerochan.get_random()

        if img:
            await self.message.respond(img[0])

    async def error_zerochan(self, error):
        raise error


@group.command()
class Rule34(Command):
    __aliases__ = [
        "r34",
    ]

    def __init__(self):
        super().__init__(name="rule34")

    @property
    def help(self):
        return "interesting random image."

    async def rule34(self, *query_):
        query = " ".join(query_)

        channel = await self.client.rest.fetch_channel(self.message.channel_id)

        if channel.is_nsfw:
            if not query:
                chance_to_get_tip = random.randint(1, 5)

                if chance_to_get_tip == random.randint(1, 5):
                    await self.message.respond(
                        f"**Tip:** _You can provide search query to find an image you want to search._\n  Example: _{PREFIX}{self.name} femboy cock_"
                    )
                img = rule34.get_random()
            else:
                img = rule34.get_random_from_query(query)

            if img:
                await self.message.respond(img[0])
            else:
                await self.message.respond("Nothing found ¯\\_(ツ)_/¯")
        else:
            await self.message.respond(
                "You can't do it here buddy. this isn't NSFW channel!"
            )
            
    async def error_rule34(self, error):
        raise error
