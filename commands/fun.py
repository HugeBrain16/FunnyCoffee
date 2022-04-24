import random
import hikari
import requests
import cmdtools
from cmdtools.callback.option import OptionModifier
from cmdtools.callback import Callback, ErrorCallback
from bs4 import BeautifulSoup

from lib import command

group = command.BaseGroup("Fun")
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

@group.command()
class Ascii(command.BaseCommand):
    __help__ = "some kind of twitch ascii art copypasta"

    def __init__(self):
        super().__init__(name="ascii")

        self._callback = Callback(self.ascii_)
        self._callback.errcall = ErrorCallback(self.error_ascii)

        self.add_option("keyword", modifier=OptionModifier.ConsumeRest)

    @staticmethod
    def search_ascii(keyword, max_result=1, safe=True):
        req = requests.get("https://www.twitchquotes.com/copypastas/search", params={"query": keyword})
        soup = BeautifulSoup(req.text, 'html.parser')

        asciis = soup.find_all("article", {"class": "twitch-copypasta-card-ascii_art"})
        ascii_safe = []

        for ascii_ in asciis:
            tags = ascii_.find_all("h4", {"class": "tag-label"})
        
            if tags:
                tags = [tag.text.lower().strip() for tag in tags]
            
                if "nsfw" not in tags and ascii_.find("img", {"class": "-blurred-image"}) is None:
                    ascii_safe.append(ascii_)
            else:
                ascii_safe.append(ascii_)

        if safe:
            asciis = ascii_safe

        return [ascii_.find("span", {"class": "-main-text"}).text for ascii_ in asciis[:max_result]]

    async def error_ascii(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "keyword":
                await ctx.attrs.message.respond("Search keyword is required!")
        else:
            raise ctx.error

    async def ascii_(self, ctx):
        options = {}
        channel = await ctx.attrs.client.rest.fetch_channel(ctx.attrs.message.channel_id)

        if channel.is_nsfw:
            options.update({"safe": False})

        result = self.search_ascii(ctx.options.keyword, **options)

        if result:
            await ctx.attrs.message.respond(result[0][:2000])
        else:
            await ctx.attrs.message.respond("Not found: " + ctx.options.keyword)
