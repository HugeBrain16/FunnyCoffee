import os
import re
import json
import random
import datetime
import logging
import asyncio

import hikari
import cmdtools
from cmdtools.ext.command import RunnerError

from lib import utils
from lib import meta


if os.name != "nt":
    import uvloop

    uvloop.install()


class FunnyCoffee(hikari.GatewayBot):
    def __init__(self, token: str):
        self.config = json.load(open("config.json", "r", encoding="UTF-8"))

        super().__init__(
            token=token,
        )

        # subscriptions
        self.subscribe(hikari.GuildMessageCreateEvent, self.on_message)
        self.subscribe(hikari.StartedEvent, self.on_started)
        self.subscribe(hikari.StartingEvent, self.on_starting)

    async def on_starting(self, event: hikari.StartingEvent):
        logging.info(f"Starting FunnyCoffee version v{meta.Version(0)}...")

    async def on_started(self, event: hikari.StartedEvent):
        self.loop = asyncio.get_event_loop()
        self.start_time = datetime.datetime.utcnow()
        self.commands = []
        loadcmdmsg = []
        for command in utils.get_commands():
            cmd = utils.load_command(command)

            if not hasattr(cmd, "PREFIX"):
                warnmsg = f"Command module exists, but no prefix defined: {command}"
                warnmsg += f"\n  Module contains {len(cmd.group.commands)} command(s)"
                warnmsg += "\nTo load the command module, please define PREFIX variable in global scope."
                logging.warning(warnmsg)
            else:
                self.commands.append(cmd)
                loadcmdmsg.append(f"  - {command}")
        loadcmdmsg.append(f"{len(loadcmdmsg)} Command module(s) found:")
        logging.info("\n".join(loadcmdmsg[::-1]))

        await self.update_presence(
            status=hikari.Status.IDLE,
            idle_since=datetime.datetime.now(),
            activity=hikari.Activity(
                name="the hit game Among Us", type=hikari.ActivityType.PLAYING
            ),
        )

    async def on_message(self, event: hikari.GuildMessageCreateEvent):
        if event.is_human:
            message = event.message

            # hard coding garbage
            if re.search(r"funny\s*coffee", message.content, flags=re.IGNORECASE):
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))
            elif message.content.strip() == f"<@!{self.get_me().id}>":
                await message.respond(random.choice(["hello", "yo", "hi", "hey"]))

            if re.match(
                r"^funny\s*coffee\s*prefix\s*\??$", message.content, flags=re.IGNORECASE
            ):
                await message.respond("Ask again nicely.")
            elif re.match(
                r"^funny\s*coffee\s*\,?\s*prefix\s*\,?\s*ple?a?se?.?$",
                message.content,
                flags=re.IGNORECASE,
            ):
                gcom = utils.load_command("general")

                if hasattr(gcom, "PREFIX"):
                    await message.respond(
                        f"my prefix is **{gcom.PREFIX}**, try **{gcom}help**"
                    )
                else:
                    await message.respond("No.")
            else:
                for cmd in self.commands:
                    cmdobj = cmdtools.AioCmd(message.content, prefix=cmd.PREFIX)

                    if cmdobj.name:
                        try:
                            await cmd.group.run(
                                cmdobj, attrs={"message": message, "client": self}
                            )
                        except RunnerError:
                            if self.config["logging"]["unknownCommand"]:
                                guild: hikari.RESTGuild = await self.rest.fetch_guild(
                                    message.guild_id
                                )
                                warnmsg = f"User has executed an unknown command: {message.content}"
                                warnmsg += f"\n  User:\n    Username: {message.author.username}#{message.author.discriminator}\n    ID: {message.author.id}"
                                warnmsg += f"\n  User's guild:\n    ID: {guild.id}\n    Name: {guild.name}"
                                logging.warning(warnmsg)
                        else:
                            if self.config["logging"]["executedCommand"]:
                                guild: hikari.RESTGuild = await self.rest.fetch_guild(
                                    message.guild_id
                                )
                                logmsg = f"User has executed a command: {message.content}"
                                logmsg += f"\n  User:\n    Username: {message.author.username}#{message.author.discriminator}\n"
                                logmsg += f"\n  User's guild:\n    ID: {guild.id}\n    Name: {guild.name}"
                                logging.info(logmsg)


def main():
    if ".env" in os.listdir() and os.path.isfile(".env"):
        utils.ConfigEnv(".env")

    if not os.getenv("TOKEN"):
        print("Token is required to start the bot!")
        os.environ["TOKEN"] = utils.getin(
            "Enter Discord bot token: ", "Token is required to start the bot!"
        )

    bot = FunnyCoffee(os.getenv("TOKEN"))
    opts = {}

    # if meta.Version.DEV is not meta.DevType.RELEASE:
    #     opts.update({"asyncio_debug": True, "coroutine_tracking_depth": 20})

    bot.run(**opts)


if __name__ == "__main__":
    main()
