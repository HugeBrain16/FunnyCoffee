import hikari
import requests
import cmdtools
import datetime
import random

from typing import List
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
                            details += f"Prefix: **{mod.PREFIX}**" + "\n"

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


@group.command()
class UserInfo(Command):
    __aliases__ = [
        "uinfo",
        "user",
    ]

    def __init__(self):
        super().__init__(name="userinfo")

    @property
    def help(self):
        return "Get user details"

    def get_detail(self, member: hikari.Member):
        embed = hikari.Embed()
        embed.title = member.nickname or member.username
        embed.color = member.accent_color
        embed.description = ""

        embed.set_author(name="User info")
        embed.set_thumbnail(member.guild_avatar_url or member.avatar_url)
        if member.banner_url:
            embed.set_image(member.banner_url)

        if member.is_bot:
            embed.description += "\n[BOT]"
        embed.description += f"\nUsername: **{member.username}#{member.discriminator}**"
        embed.description += f"\nID: **{member.id}**"
        embed.description += f"\nDate created: **{member.created_at.strftime('%d %B, %Y - %H:%M:%S')}**"
        embed.description += f"\nJoined at: **{member.joined_at.strftime('%d %B, %Y - %H:%M:%S')}**"
        if member.premium_since:
            embed.description += f"\nBoosting since: **{member.premium_since.strftime('%d %B, %Y - %H:%M:%S')}**"

        return embed

    async def userinfo(self):
        if self.message.mentions.user_ids:
            member = await self.client.rest.fetch_member(
                self.message.guild_id, self.message.mentions.user_ids[0]
            )

            if member:
                embed = self.get_detail(member)
                await self.message.respond(embed=embed)
        else:
            member = await self.client.rest.fetch_member(
                self.message.guild_id, self.message.author.id
            )
            embed = self.get_detail(member)
            await self.message.respond(embed=embed)

    async def error_userinfo(self, error):
        if isinstance(error, hikari.NotFoundError):
            await self.message.respond("User not found!")
        else:
            raise error


@group.command()
class GuildInfo(Command):
    __aliases__ = [
        "serverinfo",
    ]

    def __init__(self):
        super().__init__(name="guildinfo")

    @property
    def help(self):
        return "Get guild/server info"

    async def guildinfo(self):
        guild = await self.client.rest.fetch_guild(self.message.guild_id)

        if guild:
            embed = hikari.Embed()
            embed.title = guild.name
            embed.color = hikari.Color.from_rgb(*[random.randint(0, 255) for _ in range(3)])
            embed.description = ""

            embed.set_author(name="Guild info")
            if guild.icon_url:
                embed.set_thumbnail(guild.icon_url)
            if guild.banner_url:
                embed.set_image(guild.banner_url)

            embed.description += f"\nID: **{guild.id}**"
            embed.description += f"\nDate created: **{guild.created_at.strftime('%d %B, %Y - %H:%M:%S')}**"
            embed.description += f"\nRole count: **{len(guild.roles):,}**"
            embed.description += f"\nEmoji count: **{len(guild.get_emojis())}**"

            channels_field_value = ""
            channels_field_value += f"\nChannel count: **{len(guild.get_channels()):,}**"
            embed.add_field(name="Channels", value=channels_field_value, inline=False)

            members_field_value = ""
            members_field_value += f"\nMember count: **{guild.approximate_member_count:,}**"
            members_field_value += f"\nOnline member count: **{guild.approximate_active_member_count:,}**"
            members_field_value += f"\nMax members: **{guild.max_members:,}**"
            embed.add_field(name="Members", value=members_field_value, inline=False)

            owner = await guild.fetch_owner()
            owner_field_value = ""
            owner_field_value += f"\nUsername: **{owner.user.username}#{owner.user.discriminator}**"
            if owner.nickname:
                owner_field_value += f"\nNickname: **{owner.nickname}**"
            embed.add_field(name="Owner", value=owner_field_value, inline=False)

            await self.message.respond(embed=embed)

    async def error_guildinfo(self, error):
        raise error
