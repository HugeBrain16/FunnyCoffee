import random
import hikari
import requests
import cmdtools
from cmdtools.ext.command import Command, CommandWrapper


group = CommandWrapper()
PREFIX = "f+"


@group.command()
class Dice(Command):
    def __init__(self):
        self._help = "Roll a dice"
        super().__init__(name="dice")

    @property
    def help(self):
        return self._help

    async def dice(self):
        dice = random.randint(1, 6)

        await self.message.respond(f"Your dice is **{dice}**")


@group.command()
class Joke(Command):
    def __init__(self):
        self._help = "Funny jokes"
        super().__init__(name="joke")

    @property
    def help(self):
        return self._help

    async def joke(self):
        retries = 0
        url = "https://icanhazdadjoke.com/"

        joke = requests.get(url, headers={"Accept": "text/plain"})

        while joke.status_code != 200 and retries < 3:
            retries += 1
            joke = requests.get(url, headers={"Accept": "text/plain"})

            if joke.status_code == 200:
                await self.message.respond(joke.text)
                break
        else:
            if joke.status_code == 200:
                await self.message.respond(joke.text)
            else:
                await self.message.respond("Error fetching joke!")


@group.command()
class Magic8Ball(Command):
    __aliases__ = ["magic8ball", "m8ball"]

    def __init__(self):
        self._help = "a fortune-telling ball"
        super().__init__(name="8ball")

    @property
    def help(self):
        return self._help

    @property
    def callback(self):
        return self._8ball

    async def error_8ball(self, error):
        if isinstance(error, cmdtools.MissingRequiredArgument):
            if error.param == "question":
                await self.message.respond("You need to ask a question!")
        else:
            raise error

    async def _8ball(self, *question):
        if question:
            _question = " ".join(question)
        else:
            raise cmdtools.MissingRequiredArgument("invoke", "question")

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
        embed.set_author(name=_question)
        member = await self.client.rest.fetch_member(
            self.message.guild_id, self.message.author.id
        )
        embed.set_footer(text=f"Asked by {member.nickname or member.username}")

        await self.message.respond(embed=embed)
