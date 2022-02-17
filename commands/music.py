import hikari
import cmdtools
import lavasnek_rs
from cmdtools.ext.command import CommandWrapper

from lib import command

group = CommandWrapper()
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

    async def join(self):
        bot_voice_state = self.client.cache.get_voice_state(
            self.message.guild_id, self.client.get_me().id
        )

        if not bot_voice_state:
            channel_id = await join_voice_channel(self.message, self.client)

            if channel_id:
                await self.message.add_reaction("👍")
        else:
            await self.message.respond("I'm in a voice channel!")


@group.command()
class Leave(command.BaseCommand):
    __help__ = "Leaves the voice channel if connected."

    def __init__(self):
        super().__init__(name="leave")

    async def leave(self):
        bot_voice_state = self.client.cache.get_voice_state(
            self.message.guild_id, self.client.get_me().id
        )
        user_voice_state = self.client.cache.get_voice_state(
            self.message.guild_id, self.message.author.id
        )

        if bot_voice_state:
            if user_voice_state:
                if bot_voice_state.channel_id == user_voice_state.channel_id:
                    await self.client.lavalink.destroy(self.message.guild_id)
                    await self.client.lavalink.leave(self.message.guild_id)

                    await self.client.lavalink.remove_guild_node(self.message.guild_id)
                    await self.client.lavalink.remove_guild_from_loops(
                        self.message.guild_id
                    )

                    await self.message.add_reaction("👋")
                else:
                    await self.message.respond("We're not in the same voice channel!")
            else:
                await self.message.respond("You're not connected to a voice channel!")
        else:
            await self.message.respond("I'm not in a voice channel!")


@group.command()
class Stop(command.BaseCommand):
    __help__ = "Stop current song from playing."

    def __init__(self):
        super().__init__(name="stop")

    async def stop(self):
        node = await self.client.lavalink.get_guild_node(self.message.guild_id)

        if node.now_playing:
            await self.client.lavalink.stop(self.message.guild_id)
            await self.message.add_reaction("🛑")
        else:
            await self.message.respond("I'm not playing anything right now.")


@group.command()
class Pause(command.BaseCommand):
    __help__ = "Pause current song."

    def __init__(self):
        super().__init__(name="pause")

    async def pause(self):
        node = await self.client.lavalink.get_guild_node(self.message.guild_id)

        if not node.is_paused:
            await self.client.lavalink.pause(self.message.guild_id)
            await self.message.add_reaction("⏸")
        else:
            await self.message.respond("Song is currently paused!")


@group.command()
class Resume(command.BaseCommand):
    __help__ = "Resume current paused song."

    def __init__(self):
        super().__init__(name="resume")

    async def resume(self):
        node = await self.client.lavalink.get_guild_node(self.message.guild_id)

        if node.is_paused:
            await self.client.lavalink.resume(self.message.guild_id)
            await self.message.add_reaction("▶")
        else:
            await self.message.respond("Song is currently not paused!")


@group.command()
class Skip(command.BaseCommand):
    __help__ = "Skip currently playing song."

    def __init__(self):
        super().__init__(name="skip")

    async def skip(self):
        skip = await self.client.lavalink.skip(self.message.guild_id)
        node = await self.client.lavalink.get_guild_node(self.message.guild_id)

        if not skip or not node:
            await self.message.respond("Nothing to skip.")
        else:
            if not node.queue and node.now_playing:
                await self.lavalink.stop(self.message.guild_id)

            await self.message.add_reaction("⏭")


@group.command()
class Play(command.BaseCommand):
    __help__ = "Play song or add song to queue."

    def __init__(self):
        super().__init__(name="play")

    async def error_play(self, error):
        if isinstance(error, cmdtools.MissingRequiredArgument):
            if error.param == "_query":
                await self.message.respond("Search query cannot be empty!")

    async def play(self, *_query):
        if _query:
            query = " ".join(_query)
        else:
            raise cmdtools.MissingRequiredArgument("invoke", "_query")

        lavacon = self.client.lavalink.get_guild_gateway_connection_info(
            self.message.guild_id
        )

        if not lavacon:
            await join_voice_channel(self.message, self.client)

        query_info = await self.client.lavalink.auto_search_tracks(query)

        if not query_info.tracks:
            await self.message.respond(f"Nothing found from search query:\n`{query}`.")
        else:
            try:
                await self.client.lavalink.play(
                    self.message.guild_id, query_info.tracks[0]
                ).requester(self.message.author.id).queue()

                node = await self.client.lavalink.get_guild_node(self.message.guild_id)
                node.set_data(
                    {
                        "request_channel_id": self.message.channel_id,
                        "client": self.client,
                    }
                )

                await self.message.respond(
                    f"Added to queue: {query_info.tracks[0].info.title}"
                )
            except lavasnek_rs.NoSessionPresent:
                await self.message.respond("I'm not connected to a voice channel!")


@group.command()
class Queue(command.BaseCommand):
    __help__ = "Queue stuff"

    def __init__(self):
        super().__init__(name="queue")

    async def show_queue(self, client, message):
        node = await client.lavalink.get_guild_node(message.guild_id)

        if node:
            if node.queue:
                queuestr = []

                for idx, track_queue in enumerate(node.queue):
                    track = track_queue.track
                    tracknum = idx + 1
                    member = await client.rest.fetch_member(
                        message.guild_id, track_queue.requester
                    )

                    trackstr = f"{tracknum}). [{track.info.title}]({track.info.uri})"
                    trackstr += (
                        f" (Requester: {member.username}#{member.discriminator})"
                    )

                    if tracknum == 1:
                        trackstr += " (Now playing)"

                    queuestr.append(trackstr)

                    if tracknum > 10:
                        queuestr.append(f"{len(node.queue) - 10}+")
                        break

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

    async def queue(self, action="show"):
        action = action.lower()

        if action == "show":
            await self.show_queue(self.client, self.message)
        elif action == "clear":
            await self.clear_queue(self.client, self.message)
        else:
            await self.message.respond(f"Invalid action: `{action}`")
