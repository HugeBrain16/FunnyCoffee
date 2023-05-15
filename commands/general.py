import hikari
import cmdtools
import datetime
import random

from cmdtools.callback import Callback
from lib import utils
from lib import meta
from lib import command

group = command.BaseGroup("General")
PREFIX = "fc!"


@group.command("ping")
class Ping(command.BaseCommand):
    __help__ = "get latency"

    async def ping(self, ctx):
        await ctx.attrs.message.respond(
            f"Pong! (**{ctx.attrs.client.heartbeat_latency * 1000:.2f}ms**)"
        )


@group.command("avatar")
class Avatar(command.BaseCommand):
    __help__ = "Show user's avatar"

    async def avatar(self, ctx):
        mention = utils.get_mentions_ids(ctx.attrs.message.content)

        if mention:
            user = await ctx.attrs.client.rest.fetch_member(
                ctx.attrs.message.guild_id, mention[0][0]
            )

            if user:
                embed = hikari.Embed(
                    title=f"{user.nickname or user.username}'s Avatar", color=0xFFFFFF
                )
                embed.set_image(user.avatar_url)

                await ctx.attrs.message.respond(embed=embed)
            else:
                await ctx.attrs.message.respond("User not found!")
        else:
            author = await ctx.attrs.client.rest.fetch_member(
                ctx.attrs.message.guild_id, ctx.attrs.message.author.id
            )
            embed = hikari.Embed(
                title=f"{author.nickname or author.username}'s Avatar", color=0xFFFFFF
            )
            embed.set_image(author.avatar_url)

            await ctx.attrs.message.respond(embed=embed)

    async def error_avatar(self, ctx):
        if isinstance(ctx.error, hikari.NotFoundError):
            await ctx.attrs.message.respond("User not found!")
        else:
            raise ctx.error


@group.command("help")
class Help(command.BaseCommand):
    __help__ = "Show help"

    def __init__(self, name):
        super().__init__(name)

        self._callback = Callback(self.__help)

    async def __help(self, ctx):
        embed = hikari.Embed(title="Help", color=0xFFFFFF)
        embed.description = "Showing all available commands"

        for command in ctx.attrs.client.commands:
            embed.add_field(
                name=f"{command.group.name.replace('_', ' ')}: {command.PREFIX}",
                value=", ".join([cmd.name for cmd in command.group.commands]),
                inline=True,
            )

        await ctx.attrs.message.respond(embed=embed)


@group.add_option("name")
@group.command("cmd", aliases=["searchcmd", "findcmd"])
class CmdDetail(command.BaseCommand):
    __help__ = "Search for commands and the details"

    async def error_cmd(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "name":
                await ctx.attrs.message.respond("Please provide the command name!")
        else:
            raise ctx.error

    async def cmd(self, ctx):
        embed = hikari.Embed(title="Search Result", color=0x00FF00)
        embed.set_author(name="Command Details")

        for command in ctx.attrs.client.commands:
            for cobj in command.group.commands:
                if ctx.options.name in cobj.name:
                    details = ""

                    if hasattr(cobj, "help"):
                        if isinstance(cobj.help, str):
                            details += cobj.help + "\n\n"
                    if cobj.__disabled__:
                        details += "Disabled: **Yes**" + "\n"
                    else:
                        details += "Disabled: **No**" + "\n"
                    details += f"Category: **{command.group.name}**" + "\n"
                    details += f"Prefix: **{command.PREFIX}**" + "\n"

                    if cobj.aliases:
                        details += f"Aliases: {', '.join(cobj.aliases)}" + "\n"

                    embed.add_field(name=cobj.name, value=details, inline=True)

        await ctx.attrs.message.respond(embed=embed)


@group.command("info", aliases=["botinfo"])
class Info(command.BaseCommand):
    __help__ = "Get bot details"

    async def info(self, ctx):
        embed = hikari.Embed(title="FunnyCoffee", color=0x00FFFF)
        embed.set_footer(text=f"version {meta.Version(0)}")
        embed.set_thumbnail(ctx.attrs.client.get_me().avatar_url)

        embed.description = ""
        embed.description += "https://github.com/HugeBrain16/FunnyCoffee" + "\n"
        embed.description += (
            f"Latency: **{ctx.attrs.client.heartbeat_latency * 1000:.2f}ms**" + "\n"
        )
        embed.description += (
            f"Uptime: **{str(datetime.datetime.utcnow() - ctx.attrs.client.start_time)}**"
            + "\n"
        )

        await ctx.attrs.message.respond(embed=embed)


@group.command("userinfo", aliases=["uinfo", "user"])
class UserInfo(command.BaseCommand):
    __help__ = "Get user details"

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
        embed.description += (
            f"\nDate created: **{member.created_at.strftime('%d %B, %Y - %H:%M:%S')}**"
        )
        embed.description += (
            f"\nJoined at: **{member.joined_at.strftime('%d %B, %Y - %H:%M:%S')}**"
        )
        if member.premium_since:
            embed.description += f"\nBoosting since: **{member.premium_since.strftime('%d %B, %Y - %H:%M:%S')}**"

        return embed

    async def userinfo(self, ctx):
        mention = utils.get_mentions_ids(ctx.attrs.message.content)

        if mention:
            member = await ctx.attrs.client.rest.fetch_member(
                ctx.attrs.message.guild_id, mention[0][0]
            )

            if member:
                embed = self.get_detail(member)
                await ctx.attrs.message.respond(embed=embed)
        else:
            member = await ctx.attrs.client.rest.fetch_member(
                ctx.attrs.message.guild_id, ctx.attrs.message.author.id
            )
            embed = self.get_detail(member)
            await ctx.attrs.message.respond(embed=embed)

    async def error_userinfo(self, ctx):
        if isinstance(ctx.error, hikari.NotFoundError):
            await ctx.attrs.message.respond("User not found!")
        else:
            raise ctx.error


@group.command("guildinfo", aliases=["serverinfo"])
class GuildInfo(command.BaseCommand):
    __help__ = "Get guild/server info"

    async def guildinfo(self, ctx):
        guild = await ctx.attrs.client.rest.fetch_guild(ctx.attrs.message.guild_id)

        if guild:
            embed = hikari.Embed()
            embed.title = guild.name
            embed.color = hikari.Color.from_rgb(
                *[random.randint(0, 255) for _ in range(3)]
            )
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
            channels_field_value += (
                f"\nChannel count: **{len(guild.get_channels()):,}**"
            )
            embed.add_field(name="Channels", value=channels_field_value, inline=False)

            members_field_value = ""
            members_field_value += (
                f"\nMember count: **{guild.approximate_member_count:,}**"
            )
            members_field_value += (
                f"\nOnline member count: **{guild.approximate_active_member_count:,}**"
            )
            members_field_value += f"\nMax members: **{guild.max_members:,}**"
            embed.add_field(name="Members", value=members_field_value, inline=False)

            owner = await guild.fetch_owner()
            owner_field_value = ""
            owner_field_value += (
                f"\nUsername: **{owner.user.username}#{owner.user.discriminator}**"
            )
            if owner.nickname:
                owner_field_value += f"\nNickname: **{owner.nickname}**"
            embed.add_field(name="Owner", value=owner_field_value, inline=False)

            await ctx.attrs.message.respond(embed=embed)

    async def error_guildinfo(self, ctx):
        raise ctx.error
