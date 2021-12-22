import random
from cmdtools.ext.command import Command, CommandWrapper

from lib import zerochan
from lib import rule34
from lib import kitsu
from lib import command

group = CommandWrapper()

PREFIX = "m!"


@group.command()
class Zerochan(command.BaseCommand):
    __aliases__ = [
        "zchan",
    ]
    __help__ = "Get a random anime picture."

    def __init__(self):
        super().__init__(name="zerochan")

    async def zerochan(self):
        img = zerochan.get_random()

        if img:
            await self.message.respond(img[0])

    async def error_zerochan(self, error):
        raise error


@group.command()
class Rule34(command.BaseCommand):
    __aliases__ = [
        "r34",
    ]
    __help__ = "interesting random image."

    def __init__(self):
        super().__init__(name="rule34")

    async def rule34(self, *query_):
        query = " ".join(query_)
        sendtip = False
        channel = await self.client.rest.fetch_channel(self.message.channel_id)

        if channel.is_nsfw:
            if not query:
                chance_to_get_tip = random.randint(1, 5)

                if chance_to_get_tip == random.randint(1, 5):
                    sendtip = True
                img = rule34.get_random()
            else:
                img = rule34.get_random_from_query(query)

            if img:
                if sendtip is True:
                    await self.message.respond(
                        f"**Tip:** _You can provide search query to find an image you want to search._\n  Example: _{PREFIX}{self.name} femboy cock_"
                    )
                await self.message.respond(img[0])
            else:
                await self.message.respond("Nothing found ¯\\_(ツ)_/¯")
        else:
            await self.message.respond(
                "You can't do it here buddy. this isn't NSFW channel!"
            )

    async def error_rule34(self, error):
        raise error


@group.command()
class Anime(command.BaseCommand):
    __help__ = "Search for anime"

    def __init__(self):
        super().__init__(name="anime")

    async def anime(self, *query_):
        query = ""
        if query_:
            query = " ".join(query_)
            anime = kitsu.search_anime(query, limit=1)
        else:
            anime = kitsu.random_anime(limit=1)

        if anime:
            await self.message.respond(embed=anime[0].discord_embed(cover=True))
        else:
            await self.message.respond(f"Not found: '{query}'")

    async def error_anime(self, error: Exception):
        raise error
