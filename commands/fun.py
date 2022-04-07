import random
import hikari
import requests
import cmdtools
from cmdtools.ext.command import Group
from cmdtools.callback.option import OptionModifier
from cmdtools.callback import Callback, ErrorCallback

from lib import command

group = Group("Fun")
PREFIX = "f+"


@group.command()
class Dice(command.BaseCommand):
    __help__ = "Roll a dice"

    def __init__(self):
        super().__init__(name="dice")

    async def dice(self, ctx):
        dice = random.randint(1, 6)

        await ctx.attrs.message.respond(f"Your dice is **{dice}**")


@group.command()
class Joke(command.BaseCommand):
    __help__ = "Funny jokes"

    def __init__(self):
        super().__init__(name="joke")

    async def joke(self, ctx):
        retries = 0
        url = "https://icanhazdadjoke.com/"

        joke = requests.get(url, headers={"Accept": "text/plain"})
        joke.encoding = "utf-8"

        while joke.status_code != 200 and retries < 3:
            retries += 1
            joke = requests.get(url, headers={"Accept": "text/plain"})
            joke.encoding = "utf-8"

            if joke.status_code == 200:
                await ctx.attrs.message.respond(joke.text)
                break
        else:
            if joke.status_code == 200:
                await ctx.attrs.message.respond(joke.text)
            else:
                await ctx.attrs.message.respond("Error fetching joke!")


@group.command()
class Magic8Ball(command.BaseCommand):
    __aliases__ = ["magic8ball", "m8ball"]
    __help__ = "a fortune-telling ball"

    def __init__(self):
        super().__init__(name="8ball")

        self._callback = Callback(self._8ball)
        self._callback.errcall = ErrorCallback(self.error_8ball)

        self.add_option("question", modifier=OptionModifier.ConsumeRest)

    async def error_8ball(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "question":
                await ctx.attrs.message.respond("You need to ask a question!")
        else:
            raise ctx.error

    async def _8ball(self, ctx):
        answers = [
            # affirmative
            {"text": "It is certain.", "color": 0x02590F},
            {"text": "It is decidedly so.", "color": 0x02590F},
            {"text": "Without a doubt.", "color": 0x02590F},
            {"text": "Yes definitely.", "color": 0x02590F},
            {"text": "You may rely on it.", "color": 0x02590F},
            {"text": "As I see it, yes.", "color": 0x02590F},
            {"text": "Most likely.", "color": 0x02590F},
            {"text": "Outlook good.", "color": 0x02590F},
            {"text": "Yes.", "color": 0x02590F},
            {"text": "Signs point to yes.", "color": 0x02590F},
            # non-committal
            {"text": "Reply hazy, try again.", "color": 0xFFFF00},
            {"text": "Ask again later.", "color": 0xFFFF00},
            {"text": "Better not tell you now.", "color": 0xFFFF00},
            {"text": "Cannot predict now.", "color": 0xFFFF00},
            {"text": "Concentrate and ask again.", "color": 0xFFFF00},
            # negative
            {"text": "Don't count on it.", "color": 0xFF0000},
            {"text": "My reply is no.", "color": 0xFF0000},
            {"text": "My sources say no.", "color": 0xFF0000},
            {"text": "Outlook not so good.", "color": 0xFF0000},
            {"text": "Very doubtful.", "color": 0xFF0000},
        ]

        answer = random.choice(answers)
        embed = hikari.Embed(title=answer["text"], color=answer["color"])
        embed.set_thumbnail(
            "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Magic8ball.jpg/220px-Magic8ball.jpg"
        )
        embed.set_author(name=ctx.options.question)
        member = await ctx.attrs.client.rest.fetch_member(
            ctx.attrs.message.guild_id, ctx.attrs.message.author.id
        )
        embed.set_footer(text=f"Asked by {member.nickname or member.username}")

        await ctx.attrs.message.respond(embed=embed)
