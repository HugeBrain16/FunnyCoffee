import ctypes
import ctypes
import os
import re

import cmdtools
import hikari
import lavalink
from cmdtools.callback.option import OptionModifier
from lyricsgenius import Genius

from lib import cache, command

group = command.BaseGroup("Music")
PREFIX = "m+"


async def join_voice_channel(message, client):
    voice_state = client.cache.get_voice_state(message.guild_id, message.author.id)

    if not voice_state:
        return await message.respond("You're not connected to a voice channel!")

    channel_id = voice_state.channel_id

    if not channel_id:
        return await message.respond("You're not connected to a voice channel!")

    client.lavalink.player_manager.create(guild_id=message.guild_id)
    await client.update_voice_state(message.guild_id, channel_id, self_deaf=True)
    return channel_id


@group.command("join")
class Join(command.BaseCommand):
    __help__ = "Join a voice channel"

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


@group.command("leave")
class Leave(command.BaseCommand):
    __help__ = "Leaves the voice channel if connected."

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
                    player = ctx.attrs.client.lavalink.player_manager.get(
                        ctx.attrs.message.guild_id
                    )

                    if isinstance(player, lavalink.DefaultPlayer):
                        player.queue.clear()
                        await player.stop()
                        player.channel_id = None

                    await ctx.attrs.client.update_voice_state(
                        ctx.attrs.message.guild_id, None
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


@group.command("stop")
class Stop(command.BaseCommand):
    __help__ = "Stop current song from playing."

    async def stop(self, ctx):
        player = ctx.attrs.client.lavalink.player_manager.get(
            ctx.attrs.message.guild_id
        )

        if not isinstance(player, lavalink.DefaultPlayer):
            return await ctx.attrs.message.respond("Invalid opperation.")

        if player.is_playing and isinstance(player, lavalink.DefaultPlayer):
            await player.stop()
            await ctx.attrs.message.add_reaction("🛑")
        else:
            await ctx.attrs.message.respond("I'm not playing anything right now.")


@group.command("pause")
class Pause(command.BaseCommand):
    __help__ = "Pause current song."

    async def pause(self, ctx):
        player = ctx.attrs.client.lavalink.player_manager.get(
            ctx.attrs.message.guild_id
        )

        if not isinstance(player, lavalink.DefaultPlayer):
            return await ctx.attrs.message.respond("Invalid opperation.")

        if not player.paused:
            await player.set_pause(True)
            await ctx.attrs.message.add_reaction("⏸")
        else:
            await ctx.attrs.message.respond("Song is currently paused!")


@group.command("resume")
class Resume(command.BaseCommand):
    __help__ = "Resume current paused song."

    async def resume(self, ctx):
        player = ctx.attrs.client.lavalink.player_manager.get(
            ctx.attrs.message.guild_id
        )

        if not isinstance(player, lavalink.DefaultPlayer):
            return await ctx.attrs.message.respond("Invalid opperation.")

        if player.paused:
            await player.set_pause(False)
            await ctx.attrs.message.add_reaction("▶")
        else:
            await ctx.attrs.message.respond("Song is currently not paused!")


@group.command("skip")
class Skip(command.BaseCommand):
    __help__ = "Skip currently playing song."

    async def skip(self, ctx):
        player = ctx.attrs.client.lavalink.player_manager.get(
            ctx.attrs.message.guild_id
        )

        if not isinstance(player, lavalink.DefaultPlayer):
            return await ctx.attrs.message.respond("Invalid opperation.")

        if not player.queue and not player.is_playing:
            await ctx.attrs.message.respond("Nothing to skip.")
        else:
            await player.skip()
            await ctx.attrs.message.add_reaction("⏭")


@group.command("shuffle")
class Shuffle(command.BaseCommand):
    async def shuffle(self, ctx):
        player = ctx.attrs.client.lavalink.player_manager.get(
            ctx.attrs.message.guild_id
        )

        player.set_shuffle(not player.shuffle)
        await ctx.attrs.message.respond(f"Shuffle: {'ON' if player.shuffle else 'OFF'}")


@group.add_option("query", modifier=OptionModifier.ConsumeRest)
@group.command("play")
class Play(command.BaseCommand):
    __help__ = "Play song or add song to queue."

    async def error_play(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "query":
                await ctx.attrs.message.respond("Search query cannot be empty!")
        else:
            raise ctx.error

    async def play(self, ctx):
        query = ctx.options.query
        player = ctx.attrs.client.lavalink.player_manager.get(
            ctx.attrs.message.guild_id
        )

        if not player or not player.is_connected:
            channel_id = await join_voice_channel(ctx.attrs.message, ctx.attrs.client)

            if not channel_id:
                return await ctx.attrs.message.respond(
                    "Connect to a voice channel first!"
                )

        player = ctx.attrs.client.lavalink.player_manager.get(
            ctx.attrs.message.guild_id
        )

        url_rx = re.compile(r"https?://(?:www\.)?.+")
        if not url_rx.match(query):
            query = f"ytsearch:{query}"

        results = await player.node.get_tracks(query)

        if not results or not results.tracks:
            return await ctx.attrs.message.respond("Nothing found!")

        for track in results.tracks:
            track.extra.update({"request_channel_id": ctx.attrs.message.channel_id})

        if results.load_type == "PLAYLIST_LOADED":
            tracks = results.tracks

            for track in tracks:
                player.add(
                    requester=ctx.attrs.message.author.id,
                    track=track,
                )

            await ctx.attrs.message.respond(
                f"Added {len(tracks)} songs to queue from playlist {results.playlist_info.name}"
            )
        else:
            player.add(
                requester=ctx.attrs.message.author.id,
                track=results.tracks[0],
            )
            await ctx.attrs.message.respond(
                f"Added to queue: {results.tracks[0].title}"
            )

        if not player.is_playing:
            await player.play()


@group.add_option("action", default="show")
@group.command("queue")
class Queue(command.BaseCommand):
    __help__ = "Queue stuff"

    async def show_queue(self, client, message):
        player = client.lavalink.player_manager.get(message.guild_id)

        if isinstance(player, lavalink.DefaultPlayer):
            if player.queue:
                queuestr = []
                queue = []
                if player.current:
                    queue.append(player.current)
                queue.extend(player.queue)

                for idx, track in enumerate(queue):
                    tracknum = idx + 1

                    if client.config["enableCaching"]:
                        username = client.caches.get(f"{track.requester}_username")

                        if username:
                            username = username.data
                        else:
                            member = await client.rest.fetch_member(
                                message.guild_id, track.requester
                            )
                            username = f"{member.username}#{member.discriminator}"
                            cdat = cache.Cache(f"{track.requester}_username", username)
                            client.caches.store(cdat)
                    else:
                        member = await client.rest.fetch_member(
                            message.guild_id, track.requester
                        )
                        username = f"{member.username}#{member.discriminator}"

                    trackstr = f"{tracknum}). [{track.title}]({track.uri})"
                    trackstr += f" (Requester: {username})"

                    if tracknum == 1:
                        trackstr += " (Now playing)"

                    if tracknum > 10:
                        queuestr.append(f"{len(player.queue) - 10}+")
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
        player = client.lavalink.player_manager.get(message.guild_id)

        if player.queue:
            await player.stop()
            player.queue = []
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


@group.add_option("keywords", modifier=OptionModifier.ConsumeRest)
@group.command("lyrics")
class Lyrics(command.BaseCommand):
    __help__ = "Search for lyrics from Genius.com"

    async def error_lyrics(self, ctx):
        if isinstance(ctx.error, cmdtools.NotEnoughArgumentError):
            if ctx.error.option == "keywords":
                await ctx.attrs.message.respond(
                    "Please enter the keywords you want to use to search."
                )
        else:
            raise ctx.error

    async def lyrics(self, ctx):
        if "GENIUS_API" in os.environ:
            g = Genius(os.environ["GENIUS_API"])
            g.verbose = False
            g.remove_section_header = True

            song = g.search_song(ctx.options.keywords)

            if song:
                embed = hikari.embeds.Embed()
                embed.title = song.full_title
                embed.description = song.lyrics
                embed.set_thumbnail(song.song_art_image_url)
                embed.set_footer(
                    text="Genius lyrics",
                    icon="https://images.genius.com/dacc8165080a6ba33911bdda2b99437d.114x114x1.png",
                )
                embed.color = 0xFFFF00

                await ctx.attrs.message.respond(embed=embed)
            else:
                await ctx.attrs.message.respond("Unable to fetch lyrics.")
        else:
            await ctx.attrs.message.respond("this feature is unavailabe.")
