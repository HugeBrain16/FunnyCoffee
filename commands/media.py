import random
from cmdtools.ext.command import Group
from cmdtools.callback.option import OptionModifier

from lib import zerochan
from lib import rule34
from lib import kitsu
from lib import command

group = Group("Media")

PREFIX = "m!"


@group.command()
class Zerochan(command.BaseCommand):
    __aliases__ = [
        "zchan",
    ]
    __help__ = "Get a random anime picture."

    def __init__(self):
        super().__init__(name="zerochan")

    async def zerochan(self, ctx):
        img = zerochan.get_random()

        if img:
            await ctx.attrs.message.respond(img[0])

    async def error_zerochan(self, ctx):
        raise ctx.error


@group.command()
class Rule34(command.BaseCommand):
    __aliases__ = [
        "r34",
    ]
    __help__ = "interesting random image."

    def __init__(self):
        super().__init__(name="rule34")

        self.add_option("query", modifier=OptionModifier.ConsumeRest, default="")

    async def rule34(self, ctx):
        sendtip = False
        channel = await ctx.attrs.client.rest.fetch_channel(ctx.attrs.message.channel_id)

        if channel.is_nsfw:
            if not ctx.options.query:
                chance_to_get_tip = random.randint(1, 5)

                if chance_to_get_tip == random.randint(1, 5):
                    sendtip = True
                img = rule34.get_random()
            else:
                img = rule34.get_random_from_query(ctx.options.query)

            if img:
                if sendtip is True:
                    await ctx.attrs.message.respond(
                        f"**Tip:** _You can provide search query to find an image you want to search._\n  Example: _{PREFIX}{self.name} femboy cock_"
                    )
                await ctx.attrs.message.respond(img[0])
            else:
                await ctx.attrs.message.respond("Nothing found ¯\\_(ツ)_/¯")
        else:
            await ctx.attrs.message.respond(
                "You can't do it here buddy. this isn't NSFW channel!"
            )

    async def error_rule34(self, ctx):
        raise ctx.error


@group.command()
class Anime(command.BaseCommand):
    __help__ = "Search for anime"

    def __init__(self):
        super().__init__(name="anime")

        self.add_option("query", modifier=OptionModifier.ConsumeRest, default="")

    async def anime(self, ctx):
        if ctx.options.query:
            anime = kitsu.search_anime(ctx.options.query, limit=1)
        else:
            anime = kitsu.random_anime(limit=1)

        if anime:
            await ctx.attrs.message.respond(embed=anime[0].discord_embed(cover=True))
        else:
            await ctx.attrs.message.respond(f"Not found: '{ctx.options.query}'")

    async def error_anime(self, ctx):
        raise ctx.error
