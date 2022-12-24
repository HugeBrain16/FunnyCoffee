import random

from cmdtools.callback.option import OptionModifier
from danbooru import Danbooru as Booru
from hikari.embeds import Embed
from requests.exceptions import ConnectionError

from lib import command, kitsu, rule34, zerochan

group = command.BaseGroup("Media")

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
        channel = await ctx.attrs.client.rest.fetch_channel(
            ctx.attrs.message.channel_id
        )

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


@group.command()
class Danbooru(command.BaseCommand):
    __help__ = "Anime image board"

    def __init__(self):
        super().__init__(name="danbooru")

        self.add_option("tags", modifier=OptionModifier.ConsumeRest, default="")

    async def danbooru(self, ctx):
        channel = await ctx.attrs.client.rest.fetch_channel(
            ctx.attrs.message.channel_id
        )

        try:
            if channel.is_nsfw:
                booru = Booru()
            else:
                booru = Booru(host="safebooru")

            if ctx.options.tags:
                post = booru.searchs(tags=ctx.options.tags)
            else:
                post = booru.post_random()
        except ConnectionError:
            await ctx.attrs.message.respond(
                "Failed to get post!, connection timed out."
            )
            return

        if not post:
            await ctx.attrs.message.respond("Post not found!")
            return

        relpost = []
        if isinstance(post, list):
            _post = random.choice(post)
            relpost.extend(
                [f"- {booru.__base}posts/{p.id}" for p in post if p != _post][:5]
            )
            post = _post

        embed = Embed()
        if relpost:
            embed.description = "Related Posts:\n"
            embed.description += "\n".join(relpost) + "\n\n"
        else:
            embed.description = ""
        embed.description += f"Tags: **{post.tag_string if len(post.tag_string) < 128 else post.tag_string[:128] + '...'}**\n"
        if post.has_large:
            embed.set_image(post.large_file_url)
        else:
            embed.set_image(post.file_url)
        embed.set_footer(f"{booru.__base}posts/{post.id} • {post.source}")
        embed.set_author(
            name="Danbooru",
            icon="https://danbooru.donmai.us/packs/static/danbooru-logo-128x128-ea111b6658173e847734.png",
        )
        embed.color = 0x009BE6

        await ctx.attrs.message.respond(embed=embed)
