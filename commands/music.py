import hikari
import cmdtools
import lavasnek_rs
from cmdtools.callback.option import OptionModifier

from lib import command
from lib import cache

group = command.BaseGroup("Music")
PREFIX = "m+"


async def join_voice_channel(message, client):
    voice_state = client.cache.get_voice_state(message.guild_id, message.author.id)

    if not voice_state:
        await message.respond("You're not connected to a voice channel!")
        return None

    channel_id = voice_state.channel_id

    if not channel_id:
        await message.respond("You're not connected to a voice channel!")
        return None

    try:
        coninfo = await client.lavalink.join(message.guild_id, channel_id)
    except TimeoutError:
        await message.respond("Couldn't connect to voice channel.")
        return None

    await client.lavalink.create_session(coninfo)
    return channel_id


@group.command()
class Join(command.BaseCommand):
    __help__ = "Join a voice channel"

    def __init__(self):
        super().__init__(name="join")

    async def join(self, ctx):
        bot_voice_state = ctx.attrs.client.cache.get_voice_state(
            ctx.attrs.message.guild_id, ctx.attrs.client.get_me().id
        )

        if not bot_voice_state:
            channel_id = await join_voice_channel(ctx.attrs.message, ctx.attrs.client)

            if channel_id:
                await ctx.attrs.message.add_reaction("👍")
        else:
            await ctx.attrs.message.respond("I'm in a voice channel!")


@group.command()
class Leave(command.BaseCommand):
    __help__ = "Leaves the voice channel if connected."

    def __init__(self):
        super().__init__(name="leave")

    async def leave(self, ctx):
        bot_voice_state = ctx.attrs.client.cache.get_voice_state(
            ctx.attrs.message.guild_id, ctx.attrs.client.get_me().id
        )
        user_voice_state = ctx.attrs.client.cache.get_voice_state(
            ctx.attrs.message.guild_id, ctx.attrs.message.author.id
        )

        if bot_voice_state:
            if user_voice_state:
                if bot_voice_state.channel_id == user_voice_state.channel_id:
                    await ctx.attrs.client.lavalink.destroy(ctx.attrs.message.guild_id)
                    await ctx.attrs.client.lavalink.leave(ctx.attrs.message.guild_id)

                    await ctx.attrs.client.lavalink.remove_guild_node(
                        ctx.attrs.message.guild_id
                    )
                    await ctx.attrs.client.lavalink.remove_guild_from_loops(
                        ctx.attrs.message.guild_id
                    )

                    await ctx.attrs.message.add_reaction("👋")
                else:
                    await ctx.attrs.message.respond(
                        "We're not in the same voice channel!"
                    )
            else:
                await ctx.attrs.message.respond(
                    "You're not connected to a voice channel!"
                )
        else:
            await ctx.attrs.message.respond("I'm not in a voice channel!")


@group.command()
class Stop(command.BaseCommand):
    __help__ = "Stop current song from playing."

    def __init__(self):
        super().__init__(name="stop")

    async def stop(self, ctx):
        node = await ctx.attrs.client.lavalink.get_guild_node(
            ctx.attrs.message.guild_id
        )

        if node.now_playing:
            await ctx.attrs.client.lavalink.stop(ctx.attrs.message.guild_id)
            await ctx.attrs.message.add_reaction("🛑")
        else:
            await ctx.attrs.message.respond("I'm not playing anything right now.")


@group.command()
class Pause(command.BaseCommand):
    __help__ = "Pause current song."

    def __init__(self):
        super().__init__(name="pause")

    async def pause(self, ctx):
        node = await ctx.attrs.client.lavalink.get_guild_node(
            ctx.attrs.message.guild_id
        )

        if not node.is_paused:
            await ctx.attrs.client.lavalink.pause(ctx.attrs.message.guild_id)
            await ctx.attrs.message.add_reaction("⏸")
        else:
            await ctx.attrs.message.respond("Song is currently paused!")


@group.command()
class Resume(command.BaseCommand):
    __help__ = "Resume current paused song."

    def __init__(self):
        super().__init__(name="resume")

    async def resume(self, ctx):
        node = await ctx.attrs.client.lavalink.get_guild_node(
            ctx.attrs.message.guild_id
        )

        if node.is_paused:
            await ctx.attrs.client.lavalink.resume(ctx.attrs.message.guild_id)
            await ctx.attrs.message.add_reaction("▶")
        else:
            await ctx.attrs.message.respond("Song is currently not paused!")


@group.command()
class Skip(command.BaseCommand):
    __help__ = "Skip currently playing song."

    def __init__(self):
        super().__init__(name="skip")

    async def skip(self, ctx):
        skip = await ctx.attrs.client.lavalink.skip(ctx.attrs.message.guild_id)
        node = await ctx.attrs.client.lavalink.get_guild_node(
            ctx.attrs.message.guild_id
        )

        if not skip or not node:
            await ctx.attrs.message.respond("Nothing to skip.")
        else:
            if not node.queue:
                await ctx.attrs.client.lavalink.stop(ctx.attrs.message.guild_id)

            await ctx.attrs.message.add_reaction("⏭")


@group.command()
class Play(command.BaseCommand):
    __help__ = "Play song or add song to queue."

    def __init__(self):
        super().__init__(name="play")

        self.add_option("query", modifier=OptionModifier.ConsumeRest)

    async def error_play(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "query":
                await ctx.attrs.message.respond("Search query cannot be empty!")

    async def play(self, ctx):
        lavacon = ctx.attrs.client.lavalink.get_guild_gateway_connection_info(
            ctx.attrs.message.guild_id
        )

        if not lavacon:
            await join_voice_channel(ctx.attrs.message, ctx.attrs.client)

        query_info = await ctx.attrs.client.lavalink.auto_search_tracks(
            ctx.options.query
        )

        if not query_info.tracks:
            await ctx.attrs.message.respond(
                f"Nothing found from search query:\n`{query}`."
            )
        else:
            try:
                await ctx.attrs.client.lavalink.play(
                    ctx.attrs.message.guild_id, query_info.tracks[0]
                ).requester(ctx.attrs.message.author.id).queue()

                node = await ctx.attrs.client.lavalink.get_guild_node(
                    ctx.attrs.message.guild_id
                )
                node.set_data(
                    {
                        "request_channel_id": ctx.attrs.message.channel_id,
                        "client": ctx.attrs.client,
                    }
                )

                await ctx.attrs.message.respond(
                    f"Added to queue: {query_info.tracks[0].info.title}"
                )
            except lavasnek_rs.NoSessionPresent:
                await ctx.attrs.message.respond("I'm not connected to a voice channel!")


@group.command()
class Queue(command.BaseCommand):
    __help__ = "Queue stuff"

    def __init__(self):
        super().__init__(name="queue")

        self.add_option("action", default="show")

    async def show_queue(self, client, message):
        node = await client.lavalink.get_guild_node(message.guild_id)

        if node:
            if node.queue:
                queuestr = []

                for idx, track_queue in enumerate(node.queue):
                    track = track_queue.track
                    tracknum = idx + 1

                    if client.config["enableCaching"]:
                        username = client.caches.get(
                            f"{track_queue.requester}_username"
                        )

                        if username:
                            username = username.data
                        else:
                            member = await client.rest.fetch_member(
                                message.guild_id, track_queue.requester
                            )
                            username = f"{member.username}#{member.discriminator}"
                            cdat = cache.Cache(
                                f"{track_queue.requester}_username", username
                            )
                            client.caches.store(cdat)
                    else:
                        member = await client.rest.fetch_member(
                            message.guild_id, track_queue.requester
                        )
                        username = f"{member.username}#{member.discriminator}"

                    trackstr = f"{tracknum}). [{track.info.title}]({track.info.uri})"
                    trackstr += f" (Requester: {username})"

                    if tracknum == 1:
                        trackstr += " (Now playing)"

                    if tracknum > 10:
                        queuestr.append(f"{len(node.queue) - 10}+")
                        break

                    queuestr.append(trackstr)

                embed = hikari.Embed(title="Queue")
                embed.color = 0xFFFFFF
                embed.description = "\n".join(queuestr)

                embed.set_footer(
                    text=f"Requested by {message.member.nickname or message.member.username}"
                )

                await message.respond(embed=embed)
            else:
                await message.respond("Queue is empty!")

    async def clear_queue(self, client, message):
        await client.lavalink.stop(message.guild_id)
        node = await client.lavalink.get_guild_node(message.guild_id)

        if node:
            node.now_playing = None
            node.queue = []

            await client.lavalink.set_guild_node(message.guild_id, node)
            await message.respond("Queue cleared!")
        else:
            await message.respond("Queue is empty!")

    async def queue(self, ctx):
        action = ctx.options.action.lower()

        if action == "show":
            await self.show_queue(ctx.attrs.client, ctx.attrs.message)
        elif action == "clear":
            await self.clear_queue(ctx.attrs.client, ctx.attrs.message)
        else:
            await ctx.attrs.message.respond(f"Invalid action: `{action}`")
