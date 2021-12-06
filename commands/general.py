import hikari
import requests
import cmdtools
import datetime

from cmdtools.ext.command import Command, CommandWrapper
from lib import utils
from lib import meta

group = CommandWrapper()
PREFIX = "fc!"


@group.command()
class Ping(Command):
    def __init__(self):
        super().__init__(name="ping")

    @property
    def help(self):
        return "get latency"

    async def ping(self):
        await self.message.respond(
            f"Pong! (**{self.client.heartbeat_latency * 1000:.2f}ms**)"
        )


@group.command()
class Avatar(Command):
    def __init__(self):
        super().__init__(name="avatar")

    @property
    def help(self):
        return "Show user's avatar"

    async def avatar(self):
        if self.message.mentions.user_ids:
            user = await self.client.rest.fetch_member(
                self.message.guild_id, self.message.mentions.user_ids[0]
            )

            if user:
                embed = hikari.Embed(
                    title=f"{user.nickname or user.username}'s Avatar", color=0xFFFFFF
                )
                embed.set_image(user.avatar_url)

                await self.message.respond(embed=embed)
            else:
                await self.message.respond("User not found!")
        else:
            author = await self.client.rest.fetch_member(
                self.message.guild_id, self.message.author.id
            )
            embed = hikari.Embed(title=f"{author.nickname}'s Avatar", color=0xFFFFFF)
            embed.set_image(author.avatar_url)

            await self.message.respond(embed=embed)

    async def error_avatar(self, error):
        if isinstance(error, hikari.NotFoundError):
            await self.message.respond("User not found!")
        else:
            raise error


@group.command()
class Help(Command):
    def __init__(self):
        super().__init__(name="help")

    @property
    def callback(self):
        return self._help

    @property
    def help(self):
        return "Show this"

    async def _help(self):
        embed = hikari.Embed(title="Help", color=0xFFFFFF)
        embed.description = "Showing all available commands"

        for command in utils.get_commands():
            cmdobj = utils.load_command(command)

            if cmdobj and hasattr(cmdobj, "PREFIX"):
                embed.add_field(
                    name=f"{command.capitalize().replace('_', ' ')}: {cmdobj.PREFIX}",
                    value=", ".join([cmd.name for cmd in cmdobj.group.commands]),
                    inline=True,
                )

        await self.message.respond(embed=embed)


@group.command()
class HostInfo(Command):
    def __init__(self):
        super().__init__(name="hostinfo")

    @property
    def help(self):
        return "Get bot host info."

    async def hostinfo(self):
        req = requests.get("https://api.ipify.org", params={"format": "json"})

        if req.status_code == 200:
            req = requests.get("http://ip-api.com/json/" + req.json()["ip"])

            if req.status_code == 200:
                if req.json()["status"] == "success":
                    embed = hikari.Embed(title="Host Info", color=0x00FF00)
                    embed.description = f"Country: **{req.json()['country']}**\nCity: **{req.json()['city']}**\nTimezone: **{req.json()['timezone']}**"

                    await self.message.respond(embed=embed)
                else:
                    await self.message.respond("Failed to get host info!")


@group.command()
class CmdDetail(Command):
    __aliases__ = ["searchcmd", "findcmd"]

    def __init__(self):
        super().__init__(name="cmd")

    @property
    def help(self):
        return "Search for commands and the details"

    async def error_cmd(self, error):
        if isinstance(error, cmdtools.MissingRequiredArgument):
            if error.param == "name":
                await self.message.respond("Please provide the command name!")
        else:
            raise error

    async def cmd(self, name: str):
        embed = hikari.Embed(title="Search Result", color=0x00FF00)
        embed.set_author(name="Command Details")

        for command in utils.get_commands():
            mod = utils.load_command(command)

            for cobj in mod.group.commands:
                if name in cobj.name:
                    details = ""

                    if hasattr(cobj, "help"):
                        if isinstance(cobj.help, str):
                            details += cobj.help + "\n\n"
                    details += f"Category: **{command.capitalize()}**" + "\n"
                    if hasattr(mod, "PREFIX"):
                        if isinstance(mod.PREFIX, str):
                            details += f"Prefix: **{mod.prefix}**" + "\n"

                    if cobj.aliases:
                        details += f"Aliases: {', '.join(cobj.aliases)}" + "\n"

                    embed.add_field(name=cobj.name, value=details, inline=True)

        await self.message.respond(embed=embed)


@group.command()
class Info(Command):
    __aliases__ = [
        "botinfo",
    ]

    def __init__(self):
        super().__init__(name="info")

    @property
    def help(self):
        return "Get bot details"

    async def info(self):
        embed = hikari.Embed(title="FunnyCoffee", color=0x00FFFF)
        embed.set_footer(text=f"version {meta.Version(0)}")
        embed.set_thumbnail(self.client.get_me().avatar_url)

        embed.description = ""
        embed.description += "https://github.com/HugeBrain16/FunnyCoffee" + "\n"
        embed.description += (
            f"Latency: **{self.client.heartbeat_latency * 1000:.2f}ms**" + "\n"
        )
        embed.description += (
            f"Uptime: **{str(datetime.datetime.utcnow() - self.client.start_time)}**"
            + "\n"
        )

        await self.message.respond(embed=embed)
